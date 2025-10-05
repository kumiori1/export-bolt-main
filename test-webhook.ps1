# PowerShell script to test the webhook endpoint

# Build the request body and convert to JSON
$body = @{
    prompt = "---`n`n###  **PRODUCT TYPE** `n``jewelry```n`n###  **VIDEO VIBE**`n``LUXURY```n`n---`n`n###  **VIDEO TITLE**`n**Harp of David Pendant: A Timeless Treasure**`n`n###  **STRATEGIC ANALYSIS**`n`n**Product Personality:**  `nThis pendant combines spirituality and luxury, featuring 24K gold plating and innovative micro-Bible nanotechnology.`n`n**Target Emotion:**  `nEmpowerment through spirituality and appreciation of heritage.`n`n**Detected Intent:**  `nCreate a cinematic video to showcase the pendant's beauty and symbolism.`n`n**Vibe Selection Rationale:**  `nThe product's luxury materials and its historical significance suggest a sophisticated and timeless vibe.`n`n**Chosen Approach:**  `nElegant cinematography highlighting details to evoke feelings of luxury and heritage.`n`n---`n`n###  **SCENE-BY-SCENE BREAKDOWN**`n`n#### **SCENE 1: HOOK**  *[0:00-0:06]*`n- **Visual:** Close-up of the pendant glimmering under soft golden light; slow zoom-in.`n- **Voiceover:** *`"Discover the exquisite Harp of David pendant, a symbol of faith and elegance.`"*`n`n#### **SCENE 2: INTRIGUE**  *[0:06-0:12]*`n- **Visual:** A hand delicately holding the pendant, revealing its intricate design; soft focus on the background.`n- **Voiceover:** *`"Crafted with 24K gold plating, it's a timeless piece steeped in heritage.`"*`n`n#### **SCENE 3: REVEAL**  *[0:12-0:18]*`n- **Visual:** The pendant placed on a textured surface, rotating to showcase its details and the micro-Bible inside.`n- **Voiceover:** *`"Unveiling advanced micro-Bible nanotechnology, marrying innovation with tradition.`"*`n`n#### **SCENE 4: BENEFIT**  *[0:18-0:24]*`n- **Visual:** The pendant being worn by a model, enhancing her elegant outfit; background filled with warm golden hues.`n- **Voiceover:** *`"Wear your spirituality close with this luxurious accessory, perfect for any occasion.`"*`n`n#### **SCENE 5: PAYOFF**  *[0:24-0:30]*`n- **Visual:** A final close-up of the pendant, sparkling in the light; superimpose a subtle logo.`n- **Voiceover:** *`"Elevate your spirit and style. Claim your Harp of David today.`"*`n`n---`n`n###  **READY FOR PRODUCTION**`n*30-second video plan complete and optimized for AI Agent execution* `n`n--- `n`nThis plan ensures the essence of the pendant's luxury and spirituality is captured effectively, delivering an emotional resonance with the target audience."
    image_url = "https://base44.app/api/apps/68b4aa46f5d6326ab93c3ed0/files/public/68b4aa46f5d6326ab93c3ed0/1c239c9d9_Screenshot2025-09-17at141451.png"
    video_id = "test_video_final_123"
    chat_id = "chat_final_456"
    user_id = "user_final_789"
    user_email = "testuser@example.com"
    user_name = "Test User"
    is_revision = $false
    request_timestamp = "2025-01-18T12:10:00Z"
    source = "web_app"
    version = "1.0.0"
    idempotency_key = "idem_key_final_123"
    callback_url = "https://webhook.site/your-unique-url"
    webhookUrl = "http://localhost:8080/webhook"
    executionMode = "production"
}

# Convert to JSON string
$jsonBody = $body | ConvertTo-Json -Depth 5 -Compress

Write-Host "Sending webhook request..." -ForegroundColor Green
Write-Host "URL: http://localhost:8080/webhook" -ForegroundColor Yellow
Write-Host "Payload size: $($jsonBody.Length) characters" -ForegroundColor Yellow

try {
    # Send POST request
    $response = Invoke-WebRequest `
        -Uri "http://localhost:8080/webhook" `
        -Method POST `
        -Body $jsonBody `
        -ContentType "application/json" `
        -UseBasicParsing `
        -TimeoutSec 30

    Write-Host "`nResponse Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "Response Content:" -ForegroundColor Green
    $response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 5
}
catch {
    Write-Host "`nError occurred:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.Exception.Response) {
        Write-Host "Status Code: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
    }
}

Write-Host "`nTest completed!" -ForegroundColor Green