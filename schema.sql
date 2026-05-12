-- ============================================================
-- Nistula Unified Messaging Platform — PostgreSQL Schema
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- ------------------------------------------------------------
-- 1. GUESTS
-- One record per real-world guest, regardless of channel.
-- The challenge: the same person may message from WhatsApp
-- with a phone number and also book via Airbnb with an email.
-- We unify them here; channel identities are in a separate table.
-- ------------------------------------------------------------
CREATE TABLE guests (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name   VARCHAR(255) NOT NULL,
    email       VARCHAR(255) UNIQUE,
    phone       VARCHAR(50)  UNIQUE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);


-- ------------------------------------------------------------
-- 2. GUEST CHANNEL IDENTITIES
-- Links a guest to their identifier on each source channel.
-- e.g. guest X has phone +919999... on WhatsApp, and
-- airbnb_profile_id "abc123" on Airbnb.
-- This allows deduplication when the same person contacts
-- us from two different channels.
-- ------------------------------------------------------------
CREATE TABLE guest_channel_identities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    guest_id        UUID        NOT NULL REFERENCES guests(id) ON DELETE CASCADE,
    channel         VARCHAR(50) NOT NULL,  -- whatsapp | booking_com | airbnb | instagram | direct
    channel_guest_id VARCHAR(255) NOT NULL, -- phone number, profile ID, email, etc.
    UNIQUE (channel, channel_guest_id)
);


-- ------------------------------------------------------------
-- 3. PROPERTIES
-- ------------------------------------------------------------
CREATE TABLE properties (
    id          VARCHAR(50)  PRIMARY KEY,  -- e.g. "villa-b1"
    name        VARCHAR(255) NOT NULL,
    location    VARCHAR(255),
    max_guests  INT,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);


-- ------------------------------------------------------------
-- 4. RESERVATIONS
-- ------------------------------------------------------------
CREATE TABLE reservations (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_ref VARCHAR(100) NOT NULL UNIQUE,
    guest_id    UUID        NOT NULL REFERENCES guests(id),
    property_id VARCHAR(50) NOT NULL REFERENCES properties(id),
    check_in    DATE        NOT NULL,
    check_out   DATE        NOT NULL,
    num_guests  INT,
    status      VARCHAR(50) NOT NULL DEFAULT 'confirmed', -- confirmed | cancelled | completed
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ------------------------------------------------------------
-- 5. CONVERSATIONS
-- A conversation groups all messages in a single support thread.
-- One guest may have multiple conversations (one per stay, one
-- per unrelated inquiry, etc.)
-- ------------------------------------------------------------
CREATE TABLE conversations (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    guest_id        UUID        NOT NULL REFERENCES guests(id),
    reservation_id  UUID        REFERENCES reservations(id),
    property_id     VARCHAR(50) REFERENCES properties(id),
    channel         VARCHAR(50) NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'open', -- open | resolved | escalated
    opened_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ
);


-- ------------------------------------------------------------
-- 6. AGENTS
-- Human agents who review or send messages.
-- ------------------------------------------------------------
CREATE TABLE agents (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(255) NOT NULL,
    email       VARCHAR(255) NOT NULL UNIQUE,
    role        VARCHAR(50)  NOT NULL DEFAULT 'agent', -- agent | manager | admin
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ------------------------------------------------------------
-- 7. MESSAGES
-- Every inbound and outbound message across all channels.
-- Design decision: inbound AI metadata (confidence, query_type)
-- lives directly on this table rather than a join — this makes
-- reporting and filtering on AI performance straightforward
-- without extra joins on the hot query path.
-- ------------------------------------------------------------
CREATE TABLE messages (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id     UUID        NOT NULL REFERENCES conversations(id),
    guest_id            UUID        NOT NULL REFERENCES guests(id),
    direction           VARCHAR(10) NOT NULL,   -- inbound | outbound
    source_channel      VARCHAR(50) NOT NULL,
    message_text        TEXT        NOT NULL,
    timestamp           TIMESTAMPTZ NOT NULL,

    -- Classification (inbound only)
    query_type          VARCHAR(50),            -- pre_sales_availability | complaint | etc.

    -- Handling metadata (outbound only)
    ai_drafted          BOOLEAN     NOT NULL DEFAULT FALSE,
    agent_edited        BOOLEAN     NOT NULL DEFAULT FALSE,
    auto_sent           BOOLEAN     NOT NULL DEFAULT FALSE,
    sent_by_agent_id    UUID        REFERENCES agents(id),

    -- AI assessment (inbound messages)
    ai_confidence_score DECIMAL(4,3),           -- 0.000 – 1.000
    ai_action           VARCHAR(50),            -- auto_send | agent_review | escalate

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ------------------------------------------------------------
-- 8. AI DRAFTS
-- Stores the raw AI output for every inbound message.
-- Kept separate from messages so we have a full audit trail:
-- we know exactly what the AI said vs. what was actually sent.
-- ------------------------------------------------------------
CREATE TABLE ai_drafts (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    inbound_message_id  UUID        NOT NULL REFERENCES messages(id),
    drafted_reply       TEXT        NOT NULL,
    confidence_score    DECIMAL(4,3) NOT NULL,
    action              VARCHAR(50) NOT NULL,
    final_sent_text     TEXT,       -- NULL if not yet sent; may differ if agent edited
    was_sent            BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ------------------------------------------------------------
-- INDEXES
-- ------------------------------------------------------------
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_guest        ON messages(guest_id);
CREATE INDEX idx_messages_query_type   ON messages(query_type);
CREATE INDEX idx_conversations_guest   ON conversations(guest_id);
CREATE INDEX idx_conversations_status  ON conversations(status);
CREATE INDEX idx_reservations_guest    ON reservations(guest_id);
CREATE INDEX idx_channel_identities_guest ON guest_channel_identities(guest_id);


-- ============================================================
-- DESIGN DECISIONS
--
-- Hardest decision: where to store the guest identity problem.
-- A guest can contact us from WhatsApp (phone number), Airbnb
-- (profile ID), and email — all as different identifiers.
-- The guest_channel_identities table handles this by treating
-- each channel identity as a row linked to one canonical guest.
-- The hard part in production: merging two guest records when
-- you discover they are the same person. This schema supports
-- it (update guest_id on channel_identities and reassign
-- conversations/reservations), but that merge logic is
-- non-trivial and would need a dedicated service.
--
-- Second decision: keeping ai_confidence_score on the messages
-- table (denormalized from ai_drafts). This trades a small
-- amount of data duplication for much faster analytics queries
-- like "what % of messages above 0.85 confidence were later
-- edited by an agent?" without needing a join.
-- ============================================================