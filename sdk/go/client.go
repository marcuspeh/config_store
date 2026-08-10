package config

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"time"

	"github.com/hashicorp/golang-lru/v2/expirable"
)

const (
	defaultBaseURL   = "http://localhost:8001"
	defaultCacheSize = 10
	defaultCacheTTL  = 1 * time.Minute
)

// ErrNotFound is returned when the remote reports the config key does not exist.
var ErrNotFound = errors.New("config key not found")

type ConfigClient struct {
	project string
	baseURL string

	cacheSize int
	cacheTTL  time.Duration
	cache     *expirable.LRU[string, string]
}

// Option configures a ConfigClient.
type Option func(*ConfigClient)

// WithBaseURL overrides the remote endpoint (e.g. "http://config-store:6002").
func WithBaseURL(u string) Option {
	return func(c *ConfigClient) {
		if u != "" {
			c.baseURL = u
		}
	}
}

// WithCacheSize sets the maximum number of entries held in the in-memory LRU cache.
// Values <= 0 are ignored and the default is retained.
func WithCacheSize(n int) Option {
	return func(c *ConfigClient) {
		if n > 0 {
			c.cacheSize = n
			c.rebuildCache()
		}
	}
}

// WithCacheTTL replaces the TTL applied to cache entries.
// Values <= 0 are ignored and the default is retained.
func WithCacheTTL(d time.Duration) Option {
	return func(c *ConfigClient) {
		if d > 0 {
			c.cacheTTL = d
			c.rebuildCache()
		}
	}
}

// rebuildCache swaps in a fresh LRU preserving the currently configured size and TTL.
// Existing entries are discarded, which is acceptable since they'd otherwise have
// inconsistent TTL semantics across configuration changes.
func (c *ConfigClient) rebuildCache() {
	c.cache = expirable.NewLRU[string, string](c.cacheSize, nil, c.cacheTTL)
}

func NewConfigClient(project string, opts ...Option) *ConfigClient {
	c := &ConfigClient{
		project:   project,
		baseURL:   defaultBaseURL,
		cacheSize: defaultCacheSize,
		cacheTTL:  defaultCacheTTL,
	}
	c.rebuildCache()
	for _, opt := range opts {
		opt(c)
	}
	return c
}

func (c *ConfigClient) Get(ctx context.Context, key string) (string, error) {
	if value, ok := c.cache.Get(key); ok {
		return value, nil
	}

	value, err := c.getValueFromRemote(ctx, key)
	if err != nil {
		return "", err
	}

	c.cache.Add(key, value)
	return value, nil
}

func (c *ConfigClient) getValueFromRemote(ctx context.Context, key string) (string, error) {
	url := fmt.Sprintf("%s/config/%s/%s", c.baseURL, c.project, key)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return "", fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("failed to fetch from remote: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		if resp.StatusCode == http.StatusNotFound {
			return "", fmt.Errorf("%w: %s", ErrNotFound, key)
		}
		return "", fmt.Errorf("remote server returned status: %d", resp.StatusCode)
	}

	var result struct {
		Value string `json:"value"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", fmt.Errorf("failed to decode response: %w", err)
	}

	return result.Value, nil
}
