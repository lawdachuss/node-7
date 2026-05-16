package server

import (
        "encoding/json"
        "fmt"
        "os"

        "github.com/teacat/chaturbate-dvr/entity"
)

var Config *entity.Config

const settingsPath = "./conf/settings.json"

type persistedSettings struct {
        Cookies   string `json:"cookies"`
        UserAgent string `json:"user_agent"`
        ByparrURL string `json:"byparr_url"`
}

// SaveSettings writes the runtime cookies and user-agent to disk so they
// survive application restarts.
func SaveSettings() error {
        if err := os.MkdirAll("./conf", 0777); err != nil {
                return fmt.Errorf("mkdir conf: %w", err)
        }
        s := persistedSettings{
                Cookies:   Config.Cookies,
                UserAgent: Config.UserAgent,
                ByparrURL: Config.ByparrURL,
        }
        b, err := json.MarshalIndent(s, "", "  ")
        if err != nil {
                return fmt.Errorf("marshal settings: %w", err)
        }
        return os.WriteFile(settingsPath, b, 0666)
}

// LoadSettings reads persisted cookies and user-agent from disk and applies
// them to the current Config, but only when those values weren't already
// provided via CLI flags.
func LoadSettings() error {
        b, err := os.ReadFile(settingsPath)
        if os.IsNotExist(err) {
                return nil
        }
        if err != nil {
                return fmt.Errorf("read settings: %w", err)
        }
        var s persistedSettings
        if err := json.Unmarshal(b, &s); err != nil {
                return fmt.Errorf("unmarshal settings: %w", err)
        }
        if Config.Cookies == "" && s.Cookies != "" {
                Config.Cookies = s.Cookies
        }
        if Config.UserAgent == "" && s.UserAgent != "" {
                Config.UserAgent = s.UserAgent
        }
        if Config.ByparrURL == "" && s.ByparrURL != "" {
                Config.ByparrURL = s.ByparrURL
        }
        return nil
}
