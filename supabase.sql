-- ============================================================
-- VYBLA schema. Run in Supabase SQL editor.
-- ============================================================

create table if not exists users (
    id                bigint primary key,                 -- telegram user id
    username          text,
    link_code         text unique not null,               -- 6 chars A-Z0-9
    lang              text default 'ru',                  -- ru / en
    is_premium        boolean default false,
    created_at        timestamptz default now(),
    total_views       int default 0,
    total_vibes       int default 0,
    referred_by       text references users(link_code),   -- who invited this user (set once, at signup)
    referral_count    int default 0,                       -- how many people this user has referred
    referral_rewarded boolean default false                -- has the invite-3-get-premium reward been granted
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

-- key/value store used by the autonomous layer (bound channel_id, group_id, …)
create table if not exists system (
    key   text primary key,
    value text
);

create index if not exists idx_vibes_to_code   on vibes (to_user_code, created_at desc);
create index if not exists idx_vibes_feed       on vibes (is_reported, created_at desc);
create index if not exists idx_users_link_code  on users (link_code);
create index if not exists idx_users_top        on users (total_views desc);

-- Atomic counters (called via supabase rpc) --------------------------------

create or replace function increment_user_views(p_code text)
returns void language sql as $$
    update users set total_views = total_views + 1 where link_code = p_code;
$$;

create or replace function increment_user_vibes(p_code text)
returns void language sql as $$
    update users set total_vibes = total_vibes + 1 where link_code = p_code;
$$;

-- Called once, right after a NEW user is created with a referrer. Atomically
-- bumps the referrer's count and grants VYBLA+ the moment it hits the goal
-- (REFERRAL_GOAL below must match config.py's REFERRAL_GOAL).
create or replace function register_referral(p_referrer_code text)
returns table(new_count int, reward_granted boolean) language plpgsql as $$
declare
    v_count    int;
    v_rewarded boolean;
    v_granted  boolean := false;
begin
    update users
       set referral_count = referral_count + 1
     where link_code = p_referrer_code
    returning referral_count, referral_rewarded into v_count, v_rewarded;

    if v_count is null then
        return;  -- referrer code not found; nothing to do
    end if;

    if v_count >= 3 and not v_rewarded then
        update users set is_premium = true, referral_rewarded = true
         where link_code = p_referrer_code;
        v_granted := true;
    end if;

    return query select v_count, v_granted;
end;
$$;

-- Row Level Security: this bot uses the service_role key server-side, which
-- bypasses RLS. We still enable RLS so that the anon key can never read data.
alter table users  enable row level security;
alter table vibes  enable row level security;
alter table system enable row level security;
-- (No permissive policies for anon on purpose. Only service_role touches data.)
