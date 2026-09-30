-- Catalog of every uploaded sheet, and the physical table that holds its data.
-- Run this once in the Supabase SQL editor (or via `supabase db push`) before
-- the backend is deployed.

create extension if not exists pgcrypto;

create table if not exists public.dataset_catalog (
    id             uuid primary key default gen_random_uuid(),
    directory_path text not null default '',
    file_name      text not null,
    sheet_name     text not null,
    table_name     text not null unique,
    file_type      text not null check (file_type in ('xlsx', 'csv')),
    row_count      integer not null default 0,
    column_schema  jsonb not null default '[]'::jsonb,
    storage_path   text,
    uploaded_at    timestamptz not null default now(),
    updated_at     timestamptz not null default now(),
    unique (directory_path, file_name, sheet_name)
);

create index if not exists dataset_catalog_directory_idx
    on public.dataset_catalog (directory_path);

create or replace function public.set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists dataset_catalog_set_updated_at on public.dataset_catalog;
create trigger dataset_catalog_set_updated_at
    before update on public.dataset_catalog
    for each row execute function public.set_updated_at();

-- Row Level Security: this table is only ever read/written by the backend
-- using the Supabase service-role key, which bypasses RLS entirely. RLS is
-- enabled anyway so the anon/authenticated keys (if ever used client-side)
-- get no access by default.
alter table public.dataset_catalog enable row level security;

-- Private bucket for the original uploaded .xlsx / .csv files.
insert into storage.buckets (id, name, public)
values ('raw-uploads', 'raw-uploads', false)
on conflict (id) do nothing;
