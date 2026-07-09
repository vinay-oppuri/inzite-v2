# Inzite Dashboard

Next.js dashboard for the startup research assistant.

## Production Auth Decision

Authentication lives in `apps/dashboard` through Better Auth.

- Sign-in UI: `app/(auth)/sign-in/page.tsx`
- Sign-up UI: `app/(auth)/sign-up/page.tsx`
- Auth server: `app/api/auth/[...all]/route.ts`
- Auth config: `lib/auth.ts`
- Auth client: `lib/auth-client.ts`

The dashboard validates Better Auth sessions before calling the Python FastAPI
service. The service should not receive browser credentials directly; dashboard
API routes call it with `x-internal-api-key`.

## Databases

- Neon Postgres stores Better Auth tables, users, research runs, reports,
  source documents, chat sessions, and other relational app data.
- Qdrant stores vector embeddings and vector-search payloads.

Use the same Neon database for Better Auth and app data. Keep Qdrant separate
because vectors have different indexing, scaling, and backup needs from
relational data.

## Getting Started

Copy `.env.example` to `.env.local` and fill in production secrets.

Run Better Auth and app schema migrations against Neon:

```bash
bun run auth:generate
bun run db:generate
bun run db:migrate
```

Start the dashboard:

```bash
bun run dev
```

Open [http://localhost:3001](http://localhost:3001).

## Environment

Required:

```env
BETTER_AUTH_SECRET=
BETTER_AUTH_URL=
DATABASE_URL=
SERVICES_BASE_URL=
SERVICES_INTERNAL_API_KEY=
```

Optional:

```env
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
NEXT_PUBLIC_AUTH_BASE_URL=
```

## Scripts

```bash
bun run dev
bun run build
bun run check-types
bun run auth:generate
bun run auth:migrate
bun run db:generate
bun run db:migrate
bun run db:push
```

## Service Calls

Browser code should call dashboard API routes. Server routes in the dashboard
use `lib/services-client.ts` to call FastAPI with the internal service key.
