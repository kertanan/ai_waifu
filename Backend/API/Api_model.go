package main

import (
	"bytes"
	"encoding/json"
	"io/ioutil"
	"net/http"

	"github.com/gin-gonic/gin"
)

// Menangkap dari Frontend HTML
type Chatrequest struct {
	Chat string `json:"chat" binding:"required"`
}

// Untuk dikirim ke Python Flask
type FlaskRequest struct {
	Text string `json:"text"`
}

// Untuk menangkap balasan dari Python Flask
type FlaskResponse struct {
	Reply string `json:"reply"`
	Error string `json:"error"`
}

func main() {
	r := gin.Default()

	// Middleware CORS untuk Frontend HTML
	r.Use(func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type")
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}
		c.Next()
	})

	r.POST("/api/chat", func(c *gin.Context) {
		var chatReq Chatrequest

		// 1. Tangkap ketikan dari pengguna (Frontend)
		if err := c.ShouldBindJSON(&chatReq); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Format JSON salah"})
			return
		}
		userText := chatReq.Chat

		// 2. Bungkus teks tersebut ke format JSON untuk dikirim ke Python Flask
		flaskData := FlaskRequest{Text: userText}
		jsonData, _ := json.Marshal(flaskData)

		// 3. Lakukan HTTP POST ke Python Flask (Port 5000)
		resp, err := http.Post("http://localhost:5000/generate", "application/json", bytes.NewBuffer(jsonData))
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"balasan": "Maaf, server Golang gagal menghubungi otak Python (Port 5000 mati).",
			})
			return
		}
		defer resp.Body.Close()

		// 4. Baca jawaban dari Python Flask
		body, _ := ioutil.ReadAll(resp.Body)
		var flaskResp FlaskResponse
		json.Unmarshal(body, &flaskResp)

		// 5. Kembalikan balasan AI ke Frontend HTML
		if flaskResp.Error != "" {
			c.JSON(http.StatusInternalServerError, gin.H{"balasan": flaskResp.Error})
		} else {
			c.JSON(http.StatusOK, gin.H{
				"status":  "success",
				"balasan": flaskResp.Reply, // Ini adalah teks asli dari LLM!
			})
		}
	})

	r.Run(":8080")
}
