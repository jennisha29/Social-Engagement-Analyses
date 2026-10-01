use role accountadmin;

create role if not exists tweetpulse_role;

create warehouse if not exists tweetpulse_wh
    warehouse_size = xsmall
    auto_suspend = 60
    auto_resume = true
    initially_suspended = true;

create resource monitor if not exists tweetpulse_trial_monitor
    with credit_quota = 5
    frequency = monthly
    start_timestamp = immediately
    triggers on 80 percent do notify
             on 100 percent do suspend
             on 110 percent do suspend_immediate;

alter warehouse tweetpulse_wh set resource_monitor = tweetpulse_trial_monitor;

create database if not exists tweetpulse;
create schema if not exists tweetpulse.raw;
create schema if not exists tweetpulse.analytics;

grant usage on warehouse tweetpulse_wh to role tweetpulse_role;
grant usage on database tweetpulse to role tweetpulse_role;
grant usage on schema tweetpulse.raw to role tweetpulse_role;
grant usage on schema tweetpulse.analytics to role tweetpulse_role;

create or replace table tweetpulse.raw.social_posts_raw (
    raw_payload variant,
    source_filename string,
    loaded_at timestamp_ntz default current_timestamp()
);

create or replace file format tweetpulse.raw.jsonl_format
    type = json
    strip_outer_array = false;

create or replace storage integration tweetpulse_azure_storage_int
    type = external_stage
    storage_provider = 'AZURE'
    enabled = true
    azure_tenant_id = '2fb7e50e-3531-4ff0-b2bf-3e78b90709c7'
    storage_allowed_locations = ('azure://tweetpulsejp260621.blob.core.windows.net/tweetpulse-raw/raw/');

-- Run this after creating the storage integration.
-- It returns AZURE_CONSENT_URL and AZURE_MULTI_TENANT_APP_NAME.
desc integration tweetpulse_azure_storage_int;

-- Stop here first.
-- Open AZURE_CONSENT_URL in a browser, accept permissions, then grant the returned Snowflake app
-- Storage Blob Data Reader on the Azure storage account tweetpulsejp260621.

create or replace stage tweetpulse.raw.azure_social_stage
    url = 'azure://tweetpulsejp260621.blob.core.windows.net/tweetpulse-raw/raw/'
    storage_integration = tweetpulse_azure_storage_int
    file_format = tweetpulse.raw.jsonl_format;

list @tweetpulse.raw.azure_social_stage;

copy into tweetpulse.raw.social_posts_raw (raw_payload, source_filename)
from (
    select
        $1,
        metadata$filename
    from @tweetpulse.raw.azure_social_stage
)
file_format = tweetpulse.raw.jsonl_format;

create or replace view tweetpulse.analytics.vw_recent_tweets as
select
    raw_payload:tweet_id::string as tweet_id,
    raw_payload:author::string as author,
    raw_payload:text::string as text,
    raw_payload:topic::string as topic,
    raw_payload:sentiment::string as sentiment,
    raw_payload:likes::number as likes,
    raw_payload:replies::number as replies,
    raw_payload:reposts::number as reposts,
    raw_payload:engagement::number as engagement,
    try_to_timestamp_tz(raw_payload:created_at::string) as created_at,
    raw_payload:source_type::string as source_type,
    raw_payload:source_url::string as source_url,
    source_filename,
    loaded_at
from tweetpulse.raw.social_posts_raw;

create or replace view tweetpulse.analytics.vw_topic_momentum as
select
    topic,
    date_trunc('minute', created_at) as event_minute,
    count(*) as post_count,
    sum(engagement) as total_engagement,
    avg(case when sentiment = 'positive' then 1 else 0 end) as positive_rate
from tweetpulse.analytics.vw_recent_tweets
where created_at is not null
group by topic, event_minute;

grant select on all tables in schema tweetpulse.raw to role tweetpulse_role;
grant select on all views in schema tweetpulse.analytics to role tweetpulse_role;

select count(*) as loaded_rows from tweetpulse.raw.social_posts_raw;
select * from tweetpulse.analytics.vw_recent_tweets limit 20;
