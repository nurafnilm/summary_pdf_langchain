package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	_ "github.com/lib/pq"
	"github.com/redis/go-redis/v9"
)

var (
	rdb = redis.NewClient(&redis.Options{
		Addr:     "localhost:6379",
		Password: "",
		DB:       0,
	})
	queueKey = "pdf_jobs"
	db       *sql.DB
)

type JobPayload struct {
	JobID    string  `json:"job_id"`
	PDFPath  string  `json:"pdf_path"`
	Filename string  `json:"filename"`
	IsURL    bool    `json:"is_url,omitempty"`
}

type URLRequest struct {
	URL string `json:"url" binding:"required"`
}

// Init Redis & DB
func initRedisAndDB() {
	ctx := context.Background()
	_, err := rdb.Ping(ctx).Result()
	if err != nil {
		log.Fatalf("Failed to connect Redis: %v", err)
	}
	log.Println("Redis connected, queue key:", queueKey)

	db, err = sql.Open("postgres", "host=localhost port=5432 user=postgres password=pass123 dbname=pdf_summary sslmode=disable")
	if err != nil {
		log.Fatalf("Failed to connect DB: %v", err)
	}
	if err := db.Ping(); err != nil {
		log.Fatalf("DB ping failed: %v", err)
	}
	log.Println("Postgres DB connected")

	// Buat table kalau belum ada
	_, err = db.Exec(`
		CREATE TABLE IF NOT EXISTS summaries (
			job_id UUID PRIMARY KEY,
			filename TEXT NOT NULL,
			pages INTEGER DEFAULT 0,
			source TEXT NOT NULL,
			summary TEXT NOT NULL,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
		);
	`)
	if err != nil {
		log.Fatalf("Failed to create table: %v", err)
	}
	log.Println("Table summaries ready")
}

// Upload handler: Enqueue + Insert placeholder ke DB
func uploadPDF(c *gin.Context) {
	file, err := c.FormFile("file")
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "No file uploaded"})
		return
	}
	if !strings.HasSuffix(file.Filename, ".pdf") {
		c.JSON(http.StatusBadRequest, gin.H{"error": "File must be PDF"})
		return
	}

	jobID := uuid.New().String()
	tempDir := "temp"
	if err := os.MkdirAll(tempDir, 0755); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create temp dir"})
		return
	}
	tempPath := filepath.Join(tempDir, jobID+".pdf")

	tempPath, err = filepath.Abs(tempPath)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get abs path"})
		return
	}

	dst, err := os.Create(tempPath)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save file"})
		return
	}
	defer dst.Close()
	src, err := file.Open()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to open file"})
		return
	}
	defer src.Close()
	if _, err = io.Copy(dst, src); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to copy file"})
		return
	}

	// Enqueue to Redis
	payload := JobPayload{JobID: jobID, PDFPath: tempPath, Filename: file.Filename, IsURL: false}
	jsonBytes, err := json.Marshal(payload)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to marshal payload"})
		return
	}
	ctx := context.Background()
	err = rdb.LPush(ctx, queueKey, string(jsonBytes)).Err()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to enqueue job"})
		return
	}
	log.Printf("Job %s queued to Redis for %s", jobID, file.Filename)

	// Insert placeholder ke DB
	_, err = db.Exec("INSERT INTO summaries (job_id, filename, source, summary) VALUES ($1, $2, $3, $4)", jobID, file.Filename, "upload", "")
	if err != nil {
		log.Printf("Failed to insert to DB for job %s: %v", jobID, err)
	} else {
		log.Printf("Placeholder inserted to DB for job %s: %s", jobID, file.Filename)
	}

	c.JSON(http.StatusOK, gin.H{
		"job_id": jobID,
		"status": "queued",
	})
}

// Upload from URL (sama, tambah insert DB + log)
func uploadURL(c *gin.Context) {
	var req URLRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON: missing 'url'"})
		return
	}
	if !strings.HasSuffix(req.URL, ".pdf") {
		c.JSON(http.StatusBadRequest, gin.H{"error": "URL must point to a PDF"})
		return
	}

	jobID := uuid.New().String()
	tempDir := "temp"
	if err := os.MkdirAll(tempDir, 0755); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create temp dir"})
		return
	}
	tempPath := filepath.Join(tempDir, jobID+".pdf")

	tempPath, err := filepath.Abs(tempPath)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get abs path"})
		return
	}

	resp, err := http.Get(req.URL)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Failed to download PDF from URL"})
		return
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("Download failed: %d", resp.StatusCode)})
		return
	}

	dst, err := os.Create(tempPath)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to save file"})
		return
	}
	defer dst.Close()
	if _, err = io.Copy(dst, resp.Body); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to copy file"})
		return
	}

	filename := filepath.Base(req.URL)
	payload := JobPayload{JobID: jobID, PDFPath: tempPath, Filename: filename, IsURL: true}
	jsonBytes, err := json.Marshal(payload)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to marshal payload"})
		return
	}
	ctx := context.Background()
	err = rdb.LPush(ctx, queueKey, string(jsonBytes)).Err()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to enqueue job"})
		return
	}
	log.Printf("Job %s queued to Redis for URL %s", jobID, req.URL)

	// Insert placeholder ke DB
	_, err = db.Exec("INSERT INTO summaries (job_id, filename, source, summary) VALUES ($1, $2, $3, $4)", jobID, filename, "url", "")
	if err != nil {
		log.Printf("Failed to insert to DB for job %s: %v", jobID, err)
	} else {
		log.Printf("Placeholder inserted to DB for job %s: %s", jobID, filename)
	}

	c.JSON(http.StatusOK, gin.H{
		"job_id": jobID,
		"status": "queued",
	})
}

// Status poll: Query dari DB
func getStatus(c *gin.Context) {
	jobID := c.Param("job_id")
	var summaryStr string
	var pages int
	var filename string
	var source string

	err := db.QueryRow("SELECT summary, pages, filename, source FROM summaries WHERE job_id = $1", jobID).Scan(&summaryStr, &pages, &filename, &source)
	if err == sql.ErrNoRows {
		c.JSON(http.StatusOK, gin.H{"status": "processing", "job_id": jobID})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to query DB"})
		return
	}

	// Kalau summary kosong, anggap processing
	if summaryStr == "" {
		c.JSON(http.StatusOK, gin.H{"status": "processing", "job_id": jobID})
		return
	}

	log.Printf("Retrieved from DB for job %s: pages=%d, filename=%s", jobID, pages, filename)

	c.JSON(http.StatusOK, gin.H{
		"status":  "done",
		"result":  summaryStr,
		"job_id":  jobID,
	})
}

func main() {
	initRedisAndDB()
	defer rdb.Close()
	defer db.Close()

	r := gin.Default()
	r.Use(cors.Default())

	r.POST("/upload-pdf", uploadPDF)
	r.POST("/upload-url", uploadURL)
	r.GET("/status/:job_id", getStatus)
	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "OK"})
	})

	log.Println("Golang API (Redis + Postgres) starting on :8080")
	if err := r.Run(":8080"); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}