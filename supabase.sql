-- ============================================================
-- VYBLA schema. Run in Supabase SQL editor.
-- ============================================================

create table if not exists users (
    id            bigint primary key,                 -- telegram user id
    username      text,
    link_code     text unique not null,               -- 6 chars A-Z0-9
    lang          text default 'ru',                  -- ru / en
    is_premium    boolean default false,
    created_at    timestamptz default now(),
    total_views   int default 0,
    total_vibes   int default 0
);

create table if not exists vibes (
    id           uuid primary key default gen_random_uuid(),
    to_user_code text references users(link_code) on delete cascade,
    from_hash    text,                                -- hash(sender id + salt), never a real id
    mode         text,                                -- compliment | redflag | crush | custom | voice
    text         text not null,
    is_read      boolean default false,
    created_at   timestamptz default now(),
    is_reported  boolean default false
);

create index if not exists idx_vibes_to_code   on vibes (to_user_code, created_at desc);
create index if not exists idx_vibes_feed       on vibes (is_reported, created_at desc);
create index if not exists idx_users_link_code  on users (link_code);

-- Atomic counters (called via supabase rpc) --------------------------------

create or replace function increment_user_views(p_code text)
returns void language sql as $$
    update users set total_views = total_views + 1 where link_code = p_code;
$$;

create or replace function increment_user_vibes(p_code text)
returns void language sql as $$
    update users set total_vibes = total_vibes + 1 where link_code = p_code;
$$;

-- Row Level Security: this bot uses the service_role key server-side, which
-- bypasses RLS. We still enable RLS so that the anon key can never read data.
alter table users  enable row level security;
alter table vibes  enable row level security;
-- (No permissive policies for anon on purpose. Only service_role touches data.)
