--
-- PostgreSQL database dump
--

\restrict snWHfZ7JCGzfHHG27hk3YF6sySrRUKCzY17feB7gW4cEbIG30Lb1gvFh4fLSEfA

-- Dumped from database version 16.14 (Debian 16.14-1.pgdg12+1)
-- Dumped by pg_dump version 16.14 (Debian 16.14-1.pgdg12+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: guardian_consents; Type: TABLE; Schema: public; Owner: heartbeat
--

CREATE TABLE public.guardian_consents (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    guardian_phone character varying(20) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    consented_at timestamp with time zone DEFAULT now() NOT NULL,
    revoked_at timestamp with time zone
);


ALTER TABLE public.guardian_consents OWNER TO heartbeat;

--
-- Name: sessions; Type: TABLE; Schema: public; Owner: heartbeat
--

CREATE TABLE public.sessions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    refresh_token character varying(512) NOT NULL,
    user_agent character varying(255),
    ip_address inet,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    revoked_at timestamp with time zone
);


ALTER TABLE public.sessions OWNER TO heartbeat;

--
-- Name: users; Type: TABLE; Schema: public; Owner: heartbeat
--

CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email character varying(255) NOT NULL,
    nickname character varying(50) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    phone_number character varying(20),
    gender character varying(20),
    birth_date date,
    role character varying(20) DEFAULT 'user'::character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    last_login_at timestamp with time zone,
    deleted_at timestamp with time zone,
    CONSTRAINT users_role_check CHECK (((role)::text = ANY ((ARRAY['user'::character varying, 'guardian'::character varying, 'admin'::character varying])::text[])))
);


ALTER TABLE public.users OWNER TO heartbeat;

--
-- Data for Name: guardian_consents; Type: TABLE DATA; Schema: public; Owner: heartbeat
--

COPY public.guardian_consents (id, user_id, guardian_phone, is_active, consented_at, revoked_at) FROM stdin;
44444444-4444-4444-4444-444444444444	33333333-3333-3333-3333-333333333333	010-9999-9999	t	2026-05-29 14:51:35.370286+09	\N
\.


--
-- Data for Name: sessions; Type: TABLE DATA; Schema: public; Owner: heartbeat
--

COPY public.sessions (id, user_id, refresh_token, user_agent, ip_address, expires_at, created_at, revoked_at) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: heartbeat
--

COPY public.users (id, email, nickname, hashed_password, phone_number, gender, birth_date, role, is_active, created_at, last_login_at, deleted_at) FROM stdin;
11111111-1111-1111-1111-111111111111	test@example.com	테스트유저	$2b$12$AtLOiRVireV9EIXls.49cO2u4uLfJ3aun6zF.D3rnajqKVq1JQqBG	010-1111-1111	female	1995-04-12	user	t	2026-05-29 14:51:35.370286+09	\N	\N
22222222-2222-2222-2222-222222222222	admin@example.com	관리자	$2b$12$AtLOiRVireV9EIXls.49cO2u4uLfJ3aun6zF.D3rnajqKVq1JQqBG	010-2222-2222	undisclosed	1985-09-30	admin	t	2026-05-29 14:51:35.370286+09	\N	\N
33333333-3333-3333-3333-333333333333	minor@example.com	미성년사용자	$2b$12$AtLOiRVireV9EIXls.49cO2u4uLfJ3aun6zF.D3rnajqKVq1JQqBG	010-3333-3333	male	2012-07-22	user	t	2026-05-29 14:51:35.370286+09	\N	\N
\.


--
-- Name: guardian_consents guardian_consents_pkey; Type: CONSTRAINT; Schema: public; Owner: heartbeat
--

ALTER TABLE ONLY public.guardian_consents
    ADD CONSTRAINT guardian_consents_pkey PRIMARY KEY (id);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: heartbeat
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (id);


--
-- Name: sessions sessions_refresh_token_key; Type: CONSTRAINT; Schema: public; Owner: heartbeat
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_refresh_token_key UNIQUE (refresh_token);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: heartbeat
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: heartbeat
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_guardian_consents_user_id; Type: INDEX; Schema: public; Owner: heartbeat
--

CREATE INDEX idx_guardian_consents_user_id ON public.guardian_consents USING btree (user_id);


--
-- Name: idx_sessions_expires_at; Type: INDEX; Schema: public; Owner: heartbeat
--

CREATE INDEX idx_sessions_expires_at ON public.sessions USING btree (expires_at);


--
-- Name: idx_sessions_user_id; Type: INDEX; Schema: public; Owner: heartbeat
--

CREATE INDEX idx_sessions_user_id ON public.sessions USING btree (user_id);


--
-- Name: guardian_consents guardian_consents_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: heartbeat
--

ALTER TABLE ONLY public.guardian_consents
    ADD CONSTRAINT guardian_consents_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: sessions sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: heartbeat
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict snWHfZ7JCGzfHHG27hk3YF6sySrRUKCzY17feB7gW4cEbIG30Lb1gvFh4fLSEfA

