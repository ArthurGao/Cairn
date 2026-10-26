# Demo VM: one-time setup and operations

The demo runs on one Oracle Cloud Always Free VM (design §16.1, D-22): `VM.Standard.A1.Flex`,
2 OCPU / 12 GB, Ubuntu 24.04 aarch64, in the tenancy's home region. Synthetic data only.

**Private mode (the default)** — the owner alone uses it, through an SSH tunnel; no web port is
open to the internet. The text roles run on the owner's Claude subscription through
llm-gateway on the same VM.

```
VM (only SSH :22 open, to your IP)
  127.0.0.1:8080 ─ Caddy (HTTP, basic auth) ├─ /api/* → api   └─ /* → web
  127.0.0.1:7233 ─ temporal
  127.0.0.1:8787 ─ llm-gateway (systemd user service, bearer token)
  worker: host networking → 127.0.0.1:7233 and 127.0.0.1:8787
Your Mac: ssh -L 8080:127.0.0.1:8080 ubuntu@<ip>  →  http://localhost:8080
```

**The rule that keeps this within the subscription's terms: only you ever trigger a model call.**
Never give anyone the tunnel, the SSH key, the demo password or a copy of the stack. Show it by
sharing your screen. If others must use it themselves, switch to public mode (appendix), which
uses a paid gateway key for every role.

## 1. Create the VM (Oracle console)

- Shape `VM.Standard.A1.Flex`, 2 OCPU, 12 GB, image Ubuntu 24.04 (aarch64). Stay within the
  Always Free limits (A1 total 2 OCPU / 12 GB, block storage 200 GB) so nothing is billed.
- Add your SSH public key. "Out of host capacity": try another availability domain, or later.
- VCN Security List, ingress: **TCP 22 from your IP only.** Nothing else.

## 2. Harden and prepare the host (over SSH, as `ubuntu`)

The VM will hold your Claude login, so it is worth protecting like a laptop:

```bash
# SSH keys only (Oracle's Ubuntu image already disables passwords; make sure).
echo 'PasswordAuthentication no' | sudo tee /etc/ssh/sshd_config.d/90-keys-only.conf
sudo systemctl reload ssh
# Security updates applied automatically.
sudo apt-get update && sudo apt-get install -y unattended-upgrades
sudo dpkg-reconfigure -f noninteractive unattended-upgrades
```

Docker Engine from Docker's apt repository (the Ubuntu `docker.io` package lags):

```bash
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" |
  sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker ubuntu   # log out and back in
```

## 3. Secrets: `~/cairn/.env` (never in git)

```bash
mkdir -p ~/cairn
docker run --rm -it caddy:2.10.2 caddy hash-password   # prompts; the password stays out of history
```

Copy the template from your Mac, then edit it on the VM:
`scp deploy/oracle/.env.private.example ubuntu@<ip>:~/cairn/.env`.

- `COMPOSE_FILE=docker-compose.yml:docker-compose.private.yml` selects private mode.
- `DEMO_USER`, `DEMO_PASSWORD_HASH='<hash>'` (keep the single quotes).
- `CAIRN_LLMGW_TOKEN` — leave empty; step 4 fills it with the gateway's token.
- `AI_GATEWAY_API_KEY` — a **dedicated** Vercel AI Gateway key with a small budget, for the two
  roles llm-gateway cannot serve (`document.transcribe`: images; `agent.main`: tools).

```bash
chmod 600 ~/cairn/.env
```

## 4. llm-gateway on the VM

Follow llm-gateway's `docs/PRIVATE_HOST.md` (its own repo): install it, log in with the official
Claude CLI on the VM (you do this; nothing copies a token), configure `claude-sub` only, require a
bearer token (`local_token_env: LLMGW_TOKEN`; its token command also writes `CAIRN_LLMGW_TOKEN`
into `~/cairn/.env`), and run it as a systemd user service on `127.0.0.1:8787`. Check with
`llmgw doctor`.

## 5. Deploy (from your Mac, repo root, committed code only)

```bash
DEMO_USER=… DEMO_PASSWORD=… deploy/oracle/deploy.sh ubuntu@<ip>
```

It copies `git archive HEAD` to `~/cairn/releases/<sha>`, builds the images on the VM, starts
them, opens a tunnel and runs `smoke.sh` through it: the gate refuses anonymous and
wrong-password requests, `/api/health` reports the deployed commit with Temporal ok and
synthetic data, the cases page loads, and ports 80, 443, 4700, 4710, 7233, 8233, 8080 and 8787
are all closed from outside. The worker only starts once llm-gateway answers with the
`claude-sub` profile, so a running stack also means the gateway is reachable.

Rehearse both modes locally first (fixture home, fake LLM vendor, full e2e through Caddy):
`make rehearse`.

## Use it

```bash
ssh -N -L 8080:127.0.0.1:8080 ubuntu@<ip>     # keep it open while you demo
open http://localhost:8080
```

## Operations

```bash
cd ~/cairn/current/deploy/oracle
docker compose ps
docker compose logs -f --tail 100 worker api caddy
journalctl --user -u llmgw -f
```

- **Temporal UI** (VM loopback 7233 serves gRPC only): relay its UI with
  `docker run --rm -p 127.0.0.1:8233:8233 --network cairn-demo_default alpine/socat
  tcp-listen:8233,fork,reuseaddr tcp:temporal:8233`, then `ssh -L 8233:127.0.0.1:8233 …`.
- **Reset the demo data** (deletes every case, run and memory change; the sample home is
  re-seeded on the next start): `docker compose down -v && docker compose up -d --wait`.
  No backups by design: the data is synthetic and regenerable (`test/make_demo_cases.py`).
- **If the VM may be compromised:** sign the VM's Claude session out at claude.ai (account
  settings), rotate the AI Gateway key and `LLMGW_TOKEN`, then rebuild the VM.
- **Idle reclaim:** Oracle may reclaim an Always Free instance whose CPU, network and memory use
  stay under 20% for 7 days. A redeploy rebuilds everything from git; only demo data is lost.

## Appendix: public mode

For a demo other people use themselves. Every role must then run on the gateway key (never
llm-gateway), behind Caddy with TLS on `<ip>.sslip.io`, basic auth and per-IP rate limits.

- Security List: also TCP 80 and 443 (and UDP 443) from `0.0.0.0/0`.
- Oracle's Ubuntu images also filter in the host firewall (`/etc/iptables/rules.v4`):
  ```bash
  sudo iptables -I INPUT 5 -p tcp -m multiport --dports 80,443 -m state --state NEW -j ACCEPT
  sudo iptables -I INPUT 5 -p udp --dport 443 -j ACCEPT
  sudo netfilter-persistent save
  ```
- `~/cairn/.env` from `deploy/oracle/.env.example` (no `COMPOSE_FILE`, no llm-gateway lines,
  `CAIRN_HOST=<ip>.sslip.io`, a key with a budget sized for other people's use).
- `deploy.sh` then smokes `https://<ip>.sslip.io` and requires the internal ports closed.
