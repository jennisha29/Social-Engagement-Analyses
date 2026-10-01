use role accountadmin;

create role if not exists tweetpulse_role;
create warehouse if not exists tweetpulse_wh warehouse_size = xsmall auto_suspend = 60 auto_resume = true;
create resource monitor if not exists tweetpulse_trial_monitor
    with credit_quota = 5
    frequency = monthly
    start_timestamp = immediately
    triggers on 80 percent do notify
             on 100 percent do suspend
             on 110 percent do suspend_immediate;
alter warehouse tweetpulse_wh set resource_monitor = tweetpulse_trial_monitor;
grant usage on warehouse tweetpulse_wh to role tweetpulse_role;

create database if not exists tweetpulse;
create schema if not exists tweetpulse.raw;
create schema if not exists tweetpulse.analytics;
grant usage on database tweetpulse to role tweetpulse_role;
grant usage on schema tweetpulse.raw to role tweetpulse_role;
grant usage on schema tweetpulse.analytics to role tweetpulse_role;

create or replace table tweetpulse.raw.tweets_raw (
    raw_payload variant,
    loaded_at timestamp_ntz default current_timestamp()
);

create or replace file format tweetpulse.raw.jsonl_format
    type = json
    strip_outer_array = false;

-- Replace tenant ID and Azure URL before running.
create or replace storage integration tweetpulse_azure_storage_int
    type = external_stage
    storage_provider = 'AZURE'
    enabled = true
    azure_tenant_id = '<AZURE_TENANT_ID>'
    storage_allowed_locations = ('azure://<AZURE_STORAGE_ACCOUNT>.blob.core.windows.net/tweetpulse-raw/raw/');

-- After creating the storage integration, run:
-- desc integration tweetpulse_azure_storage_int;
-- Open AZURE_CONSENT_URL, accept permissions, then assign Storage Blob Data Reader to AZURE_MULTI_TENANT_APP_NAME in Azure IAM.

create or replace stage tweetpulse.raw.azure_tweet_stage
    url = 'azure://<AZURE_STORAGE_ACCOUNT>.blob.core.windows.net/tweetpulse-raw/raw/'
    storage_integration = tweetpulse_azure_storage_int
    file_format = tweetpulse.raw.jsonl_format;

-- Replace queue URL after creating the Azure Storage Queue and Event Grid subscription.
create or replace notification integration tweetpulse_azure_queue_int
    enabled = true
    type = queue
    notification_provider = azure_storage_queue
    azure_storage_queue_primary_uri = 'https://<QUEUE_STORAGE_ACCOUNT>.queue.core.windows.net/<QUEUE_NAME>'
    azure_tenant_id = '<AZURE_TENANT_ID>';

create or replace pipe tweetpulse.raw.tweets_pipe
    auto_ingest = true
    integration = tweetpulse_azure_queue_int
as
copy into tweetpulse.raw.tweets_raw (raw_payload)
from @tweetpulse.raw.azure_tweet_stage
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
    raw_payload:created_at::timestamp_tz as created_at,
    loaded_at
from tweetpulse.raw.tweets_raw;

create or replace view tweetpulse.analytics.vw_topic_momentum as
select
    topic,
    date_trunc('minute', created_at) as event_minute,
    count(*) as tweet_count,
    sum(engagement) as total_engagement,
    avg(case when sentiment = 'positive' then 1 else 0 end) as positive_rate
from tweetpulse.analytics.vw_recent_tweets
group by topic, event_minute;

grant select on all tables in schema tweetpulse.raw to role tweetpulse_role;
grant select on all views in schema tweetpulse.analytics to role tweetpulse_role;
