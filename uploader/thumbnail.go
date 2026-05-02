package uploader

import (
"encoding/json"
"fmt"
"io"
"log"
"mime/multipart"
"net/http"
"os"
"path/filepath"
"strings"
"time"
)

// ThumbnailUploader handles uploading thumbnail images to ImgBB
type ThumbnailUploader struct {
apiKey string
client *http.Client
}

// imgBBResponse is the JSON response from the ImgBB API
type imgBBResponse struct {
Data struct {
ID         string `json:"id"`
URL        string `json:"url"`
DisplayURL string `json:"display_url"`
Image      struct {
URL string `json:"url"`
} `json:"image"`
Thumb struct {
URL string `json:"url"`
} `json:"thumb"`
} `json:"data"`
Success bool `json:"success"`
Status  int  `json:"status"`
Error   struct {
Message string `json:"message"`
} `json:"error"`
}

// NewThumbnailUploader creates a new ImgBB thumbnail uploader.
// apiKey is the ImgBB API key from https://api.imgbb.com/
func NewThumbnailUploader(apiKey string) *ThumbnailUploader {
return &ThumbnailUploader{
apiKey: apiKey,
client: &http.Client{
Timeout: 2 * time.Minute,
},
}
}

// Upload uploads a thumbnail image to ImgBB and returns the direct image URL.
func (t *ThumbnailUploader) Upload(thumbnailPath string) (string, error) {
if t.apiKey == "" {
return "", fmt.Errorf("ImgBB API key not configured")
}

log.Printf("Uploading thumbnail to ImgBB: %s", thumbnailPath)

file, err := os.Open(thumbnailPath)
if err != nil {
return "", fmt.Errorf("open file: %w", err)
}
defer file.Close()

// Build multipart form via pipe to avoid buffering the whole image in memory
pr, pw := io.Pipe()
writer := multipart.NewWriter(pw)

errCh := make(chan error, 1)
go func() {
defer pw.Close()
part, err := writer.CreateFormFile("image", filepath.Base(thumbnailPath))
if err != nil {
errCh <- fmt.Errorf("create form file: %w", err)
writer.Close()
return
}
if _, err := io.Copy(part, file); err != nil {
errCh <- fmt.Errorf("copy file: %w", err)
writer.Close()
return
}
errCh <- writer.Close()
}()

uploadURL := fmt.Sprintf("https://api.imgbb.com/1/upload?key=%s", t.apiKey)
req, err := http.NewRequest("POST", uploadURL, pr)
if err != nil {
return "", fmt.Errorf("create request: %w", err)
}
req.Header.Set("Content-Type", writer.FormDataContentType())

resp, err := t.client.Do(req)
if err != nil {
	pr.CloseWithError(err) // unblock the writer goroutine
	<-errCh               // drain to avoid goroutine leak
	return "", fmt.Errorf("send request: %w", err)
}
defer resp.Body.Close()

// Wait for the writer goroutine to finish
if werr := <-errCh; werr != nil {
	return "", werr
}

body, err := io.ReadAll(resp.Body)
if err != nil {
return "", fmt.Errorf("read response: %w", err)
}

if resp.StatusCode != http.StatusOK {
return "", fmt.Errorf("ImgBB returned status %d: %s", resp.StatusCode, string(body))
}

var result imgBBResponse
if err := json.Unmarshal(body, &result); err != nil {
return "", fmt.Errorf("decode response: %w", err)
}

if !result.Success {
msg := result.Error.Message
if msg == "" {
msg = fmt.Sprintf("status %d", result.Status)
}
return "", fmt.Errorf("ImgBB upload failed: %s", msg)
}

// Prefer the direct image URL; fall back through the chain
imageURL := result.Data.Image.URL
if imageURL == "" {
imageURL = result.Data.URL
}
if imageURL == "" {
imageURL = result.Data.DisplayURL
}
imageURL = strings.TrimSpace(imageURL)
if imageURL == "" {
return "", fmt.Errorf("ImgBB returned no image URL")
}

log.Printf("Thumbnail uploaded to ImgBB: %s", imageURL)
return imageURL, nil
}