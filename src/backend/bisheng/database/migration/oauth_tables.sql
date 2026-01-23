-- OAuth Tables Migration Script
-- This script creates the necessary tables for OAuth 2.0 authentication
-- Used for third-party application authorization and text tracing API access

-- ============================================================================
-- Table: oauth_application
-- Description: Stores registered OAuth applications that can request access
--              to user resources through the OAuth 2.0 flow
-- ============================================================================
CREATE TABLE IF NOT EXISTS oauth_application (
    id VARCHAR(64) PRIMARY KEY COMMENT 'Unique application identifier',
    name VARCHAR(128) NOT NULL COMMENT 'Application display name',
    client_id VARCHAR(64) NOT NULL COMMENT 'OAuth client identifier',
    client_secret VARCHAR(128) NOT NULL COMMENT 'OAuth client secret (hashed)',
    redirect_uri VARCHAR(512) NOT NULL COMMENT 'Authorized redirect URI for OAuth callback',
    user_id INT NOT NULL COMMENT 'ID of the user who registered this application',
    status TINYINT DEFAULT 1 COMMENT 'Application status: 1=active, 0=disabled',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Record last update timestamp',
    UNIQUE KEY uk_client_id (client_id),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='OAuth application registration table';

-- ============================================================================
-- Table: oauth_authorization_code
-- Description: Stores temporary authorization codes issued during the OAuth
--              authorization code flow. Codes are short-lived and single-use.
-- ============================================================================
CREATE TABLE IF NOT EXISTS oauth_authorization_code (
    code VARCHAR(128) PRIMARY KEY COMMENT 'Authorization code (single-use)',
    client_id VARCHAR(64) NOT NULL COMMENT 'OAuth client identifier',
    user_id INT NOT NULL COMMENT 'ID of the user who authorized access',
    redirect_uri VARCHAR(512) NOT NULL COMMENT 'Redirect URI used in authorization request',
    expires_at DATETIME NOT NULL COMMENT 'Code expiration timestamp',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
    INDEX idx_client_id (client_id),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='OAuth authorization code table';

-- ============================================================================
-- Table: oauth_token
-- Description: Stores access tokens and refresh tokens issued to OAuth clients.
--              Access tokens are used to authenticate API requests.
-- ============================================================================
CREATE TABLE IF NOT EXISTS oauth_token (
    id VARCHAR(64) PRIMARY KEY COMMENT 'Unique token record identifier',
    access_token VARCHAR(256) NOT NULL COMMENT 'Access token for API authentication',
    refresh_token VARCHAR(256) NOT NULL COMMENT 'Refresh token for obtaining new access tokens',
    client_id VARCHAR(64) NOT NULL COMMENT 'OAuth client identifier',
    user_id INT NOT NULL COMMENT 'ID of the user who authorized access',
    expires_at DATETIME NOT NULL COMMENT 'Access token expiration timestamp',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
    UNIQUE KEY uk_access_token (access_token),
    UNIQUE KEY uk_refresh_token (refresh_token),
    INDEX idx_client_id (client_id),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='OAuth token table';
