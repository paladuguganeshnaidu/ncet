-- Apply only to a dedicated SyntaxLab Supabase project (not an unrelated project).
create table if not exists public.validation_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  kind text not null check (kind in ('email','url')),
  input_value text not null check (char_length(input_value) <= 2048),
  accepted boolean not null,
  steps integer not null check (steps between 1 and 4096),
  rule text not null default '',
  created_at timestamptz not null default now()
);
create index if not exists validation_runs_user_created_idx on public.validation_runs(user_id, created_at desc);
alter table public.validation_runs enable row level security;
create policy "Users can read their own runs" on public.validation_runs for select to authenticated using ((select auth.uid()) = user_id);
create policy "Users can insert their own runs" on public.validation_runs for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "Users can delete their own runs" on public.validation_runs for delete to authenticated using ((select auth.uid()) = user_id);
grant select,insert,delete on public.validation_runs to authenticated;
