\getenv developer_password DEVELOPER_PASSWORD
\getenv app_password APP_PASSWORD

CREATE ROLE issuedigest_owner NOLOGIN;
CREATE ROLE "DigestWorks_Jaesin" LOGIN PASSWORD :'developer_password'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION CONNECTION LIMIT 10;
CREATE ROLE issuedigest_app LOGIN PASSWORD :'app_password'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION CONNECTION LIMIT 20;
GRANT issuedigest_owner TO "DigestWorks_Jaesin";
CREATE DATABASE issuedigest OWNER issuedigest_owner;
REVOKE ALL ON DATABASE issuedigest FROM PUBLIC;
GRANT CONNECT ON DATABASE issuedigest TO "DigestWorks_Jaesin", issuedigest_app;
REVOKE CONNECT ON DATABASE postgres, template1 FROM PUBLIC;
ALTER ROLE "DigestWorks_Jaesin" IN DATABASE issuedigest SET role TO issuedigest_owner;

\connect issuedigest
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO issuedigest_app;
ALTER DEFAULT PRIVILEGES FOR ROLE issuedigest_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO issuedigest_app;
ALTER DEFAULT PRIVILEGES FOR ROLE issuedigest_owner IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO issuedigest_app;
