package config

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/hashicorp/golang-lru/v2/expirable"
)

type ConfigClient struct {
	project string
	baseURL string
	cache   *expirable.LRU[string, string]
}

func NewConfigClient(project string) *ConfigClient {
	return &ConfigClient{
		project: project,
		baseURL: "http://localhost:8001",
		cache:   expirable.NewLRU[string, string](10, nil, 1*time.Minute),
	}
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
			return "", fmt.Errorf("config key not found: %s", key)
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
