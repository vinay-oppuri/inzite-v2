import { relations, sql } from "drizzle-orm";
import {
  index,
  jsonb,
  pgTable,
  text,
  timestamp,
  uniqueIndex,
  uuid,
} from "drizzle-orm/pg-core";

import { user } from "./auth-schema";

export const researchRuns = pgTable(
  "research_runs",
  {
    id: text("id").primaryKey(),
    userId: text("user_id")
      .notNull()
      .references(() => user.id, { onDelete: "cascade" }),
    ideaRaw: text("idea_raw").notNull(),
    status: text("status").notNull(),
    errorLog: jsonb("error_log")
      .$type<string[]>()
      .notNull()
      .default(sql`'[]'::jsonb`),
    createdAt: timestamp("created_at").defaultNow().notNull(),
    updatedAt: timestamp("updated_at")
      .defaultNow()
      .$onUpdate(() => new Date())
      .notNull(),
  },
  (table) => [
    index("research_runs_user_id_idx").on(table.userId),
    index("research_runs_status_idx").on(table.status),
  ],
);

export const reports = pgTable(
  "reports",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    researchRunId: text("research_run_id")
      .notNull()
      .references(() => researchRuns.id, { onDelete: "cascade" }),
    markdown: text("markdown").notNull(),
    strategyReport: jsonb("strategy_report").$type<Record<string, unknown> | null>(),
    finalReportJson: jsonb("final_report_json").$type<Record<string, unknown> | null>(),
    createdAt: timestamp("created_at").defaultNow().notNull(),
    updatedAt: timestamp("updated_at")
      .defaultNow()
      .$onUpdate(() => new Date())
      .notNull(),
  },
  (table) => [uniqueIndex("reports_research_run_id_idx").on(table.researchRunId)],
);

export const sourceDocuments = pgTable(
  "source_documents",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    researchRunId: text("research_run_id")
      .notNull()
      .references(() => researchRuns.id, { onDelete: "cascade" }),
    docId: text("doc_id").notNull(),
    agent: text("agent").notNull(),
    title: text("title").notNull(),
    content: text("content").notNull(),
    sourceUrl: text("source_url"),
    publishedAt: timestamp("published_at"),
    metadata: jsonb("metadata").$type<Record<string, unknown> | null>(),
    createdAt: timestamp("created_at").defaultNow().notNull(),
  },
  (table) => [
    uniqueIndex("source_documents_run_doc_id_idx").on(table.researchRunId, table.docId),
    index("source_documents_research_run_id_idx").on(table.researchRunId),
    index("source_documents_agent_idx").on(table.agent),
  ],
);

export const chatSessions = pgTable(
  "chat_sessions",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    researchRunId: text("research_run_id")
      .notNull()
      .references(() => researchRuns.id, { onDelete: "cascade" }),
    messages: jsonb("messages")
      .$type<Array<Record<string, unknown>>>()
      .notNull()
      .default(sql`'[]'::jsonb`),
    createdAt: timestamp("created_at").defaultNow().notNull(),
    updatedAt: timestamp("updated_at")
      .defaultNow()
      .$onUpdate(() => new Date())
      .notNull(),
  },
  (table) => [index("chat_sessions_research_run_id_idx").on(table.researchRunId)],
);

export const researchRunRelations = relations(researchRuns, ({ one, many }) => ({
  user: one(user, {
    fields: [researchRuns.userId],
    references: [user.id],
  }),
  report: one(reports),
  sourceDocuments: many(sourceDocuments),
  chatSessions: many(chatSessions),
}));

export const reportRelations = relations(reports, ({ one }) => ({
  researchRun: one(researchRuns, {
    fields: [reports.researchRunId],
    references: [researchRuns.id],
  }),
}));

export const sourceDocumentRelations = relations(sourceDocuments, ({ one }) => ({
  researchRun: one(researchRuns, {
    fields: [sourceDocuments.researchRunId],
    references: [researchRuns.id],
  }),
}));

export const chatSessionRelations = relations(chatSessions, ({ one }) => ({
  researchRun: one(researchRuns, {
    fields: [chatSessions.researchRunId],
    references: [researchRuns.id],
  }),
}));
