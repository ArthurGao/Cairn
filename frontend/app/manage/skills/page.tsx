"use client";

import { useQuery } from "@tanstack/react-query";

import { PageHeader } from "@/components/PageHeader";
import { Empty, ErrorState, Loading } from "@/components/States";
import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/fetch";
import { keys } from "@/lib/api/queries";

/** The skill catalog (design §12.1): what the agent can load, by source, with L1/L2 sizes. */
export default function SkillsPage() {
  const skills = useQuery({ queryKey: keys.skills, queryFn: async () => unwrap(await api.GET("/api/skills")) });
  const checklists = useQuery({
    queryKey: keys.checklists,
    queryFn: async () => unwrap(await api.GET("/api/checklists")),
  });
  const items = new Map((checklists.data ?? []).map((c) => [c.skill, c]));
  return (
    <div className="grid grid-cols-12 gap-x-6 gap-y-8">
      <PageHeader crumbs={[{ label: "Manage" }]} title="Skills" />
      <section className="col-span-12">
        {skills.isPending ? (
          <Loading label="Loading skills…" />
        ) : skills.isError ? (
          <ErrorState error={skills.error} what="skills" />
        ) : skills.data.length === 0 ? (
          <Empty>No skills in this harness home.</Empty>
        ) : (
          [...new Set(skills.data.map((s) => s.source))].map((source) => (
            <div key={source} className="mb-8">
              <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide">
                {source === "local" ? "Local" : <span className="font-mono normal-case">{source}</span>}
                {source !== "local" && <span className="ml-2 text-xs font-normal text-muted">read-only mount</span>}
              </h2>
              <ul className="border-t border-ink text-sm">
                {skills.data
                  .filter((s) => s.source === source)
                  .map((skill) => {
                    const checklist = items.get(skill.name);
                    return (
                      <li key={skill.name} data-testid="skill" className="grid grid-cols-12 gap-3 border-b border-rule py-3">
                        <div className="col-span-12 md:col-span-7">
                          <div className="font-mono">{skill.name}</div>
                          <p className="text-xs text-muted">{skill.description}</p>
                          {checklist && checklist.items.length > 0 && (
                            <ol className="mt-2 grid gap-1 text-xs" aria-label={`${skill.name} checklist`}>
                              {checklist.items.map((item) => (
                                <li key={item.id}>
                                  <span className="font-mono text-muted">{item.id}</span> {item.requirement}
                                </li>
                              ))}
                            </ol>
                          )}
                        </div>
                        <div className="col-span-12 text-xs md:col-span-5">
                          <div>
                            L1 SKILL.md body <span className="num font-mono">{skill.body_chars}</span> chars
                          </div>
                          {skill.references.map((ref) => (
                            <div key={ref.path}>
                              L2 <span className="font-mono">{ref.path}</span>{" "}
                              <span className="num font-mono">{ref.chars}</span> chars
                            </div>
                          ))}
                        </div>
                      </li>
                    );
                  })}
              </ul>
            </div>
          ))
        )}
      </section>
    </div>
  );
}
