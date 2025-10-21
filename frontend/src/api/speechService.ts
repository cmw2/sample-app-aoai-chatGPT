/**
 * Speech-to-Text WebSocket service for real-time speech recognition
 * Handles connection to the backend speech streaming endpoint
 */

export interface SpeechConfig {
  enabled: boolean
  language: string
  region: string
  supported_languages: string[]
  audio_format: {
    sample_rate: number
    channels: number
    bit_depth: number
    format: string
  }
}

export interface SpeechResult {
  type: 'recognizing' | 'recognized' | 'error' | 'session_started' | 'session_stopped'
  text?: string
  is_final?: boolean
  confidence?: number
  offset?: number
  duration?: number
  error?: string
  session_id?: string
  timestamp?: number
}

export interface SpeechServiceCallbacks {
  onRecognizing?: (text: string) => void
  onRecognized?: (text: string, confidence: number) => void
  onError?: (error: string) => void
  onSessionStarted?: () => void
  onSessionStopped?: () => void
  onConnectionStateChange?: (state: 'connecting' | 'connected' | 'disconnected' | 'error') => void
}

export class SpeechService {
  private websocket: WebSocket | null = null
  private sessionId: string | null = null
  private callbacks: SpeechServiceCallbacks = {}
  private reconnectAttempts = 0
  private maxReconnectAttempts = 3
  private reconnectDelay = 1000
  private isConnecting = false

  constructor(private baseUrl: string = '') {
    // Use current origin if no baseUrl provided
    if (!this.baseUrl) {
      this.baseUrl = window.location.origin.replace('http', 'ws')
    }
  }

  /**
   * Get speech service configuration from the backend
   */
  async getConfig(): Promise<SpeechConfig | null> {
    try {
      const response = await fetch(`${window.location.origin}/speech/config`)
      if (!response.ok) {
        throw new Error(`Failed to get speech config: ${response.status}`)
      }
      return await response.json()
    } catch (error) {
      console.error('Error getting speech config:', error)
      return null
    }
  }

  /**
   * Set callbacks for speech events
   */
  setCallbacks(callbacks: SpeechServiceCallbacks) {
    this.callbacks = { ...this.callbacks, ...callbacks }
  }

  /**
   * Connect to the speech WebSocket endpoint
   */
  async connect(): Promise<boolean> {
    if (this.websocket?.readyState === WebSocket.OPEN) {
      console.log('Speech service already connected')
      return true
    }

    if (this.isConnecting) {
      console.log('Speech service connection already in progress')
      return false
    }

    this.isConnecting = true
    this.callbacks.onConnectionStateChange?.('connecting')

    try {
      const wsUrl = `${this.baseUrl.replace('http', 'ws')}/speech/stream`
      console.log('Connecting to speech service:', wsUrl)

      this.websocket = new WebSocket(wsUrl)

      return new Promise((resolve, reject) => {
        const connectTimeout = setTimeout(() => {
          this.cleanup()
          reject(new Error('Connection timeout'))
        }, 10000) // 10 second timeout

        this.websocket!.onopen = () => {
          clearTimeout(connectTimeout)
          this.isConnecting = false
          this.reconnectAttempts = 0
          this.callbacks.onConnectionStateChange?.('connected')
          console.log('Speech service connected')
          resolve(true)
        }

        this.websocket!.onmessage = (event) => {
          this.handleMessage(event.data)
        }

        this.websocket!.onclose = (event) => {
          clearTimeout(connectTimeout)
          this.isConnecting = false
          this.callbacks.onConnectionStateChange?.('disconnected')
          console.log('Speech service disconnected:', event.code, event.reason)
          
          if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect()
          }
        }

        this.websocket!.onerror = (error) => {
          clearTimeout(connectTimeout)
          this.isConnecting = false
          this.callbacks.onConnectionStateChange?.('error')
          console.error('Speech service error:', error)
          reject(error)
        }
      })
    } catch (error) {
      this.isConnecting = false
      this.callbacks.onConnectionStateChange?.('error')
      console.error('Failed to connect to speech service:', error)
      return false
    }
  }

  /**
   * Disconnect from the speech service
   */
  disconnect() {
    if (this.websocket) {
      this.websocket.close(1000, 'Client disconnect')
      this.cleanup()
    }
  }

  /**
   * Send audio data to the speech service
   */
  sendAudioData(audioData: ArrayBuffer) {
    if (this.websocket?.readyState === WebSocket.OPEN) {
      this.websocket.send(audioData)
    } else {
      console.warn('Cannot send audio data: WebSocket not connected')
    }
  }

  /**
   * Send control message to the speech service
   */
  sendControlMessage(command: string, data?: any) {
    if (this.websocket?.readyState === WebSocket.OPEN) {
      const message = {
        command,
        ...data
      }
      this.websocket.send(JSON.stringify(message))
    } else {
      console.warn('Cannot send control message: WebSocket not connected')
    }
  }

  /**
   * Stop speech recognition
   */
  stopRecognition() {
    this.sendControlMessage('stop_recognition')
  }

  /**
   * Add phrase hints to improve recognition
   */
  addPhraseHints(phrases: string[]) {
    this.sendControlMessage('add_phrase_hints', { phrases })
  }

  /**
   * Get connection state
   */
  getConnectionState(): 'connecting' | 'connected' | 'disconnected' | 'error' {
    if (this.isConnecting) return 'connecting'
    if (this.websocket?.readyState === WebSocket.OPEN) return 'connected'
    return 'disconnected'
  }

  /**
   * Handle incoming WebSocket messages
   */
  private handleMessage(data: string) {
    try {
      const result: SpeechResult = JSON.parse(data)
      
      switch (result.type) {
        case 'session_started':
          this.sessionId = result.session_id || null
          this.callbacks.onSessionStarted?.()
          break
          
        case 'recognizing':
          if (result.text) {
            this.callbacks.onRecognizing?.(result.text)
          }
          break
          
        case 'recognized':
          if (result.text) {
            this.callbacks.onRecognized?.(result.text, result.confidence || 1.0)
          }
          break
          
        case 'error':
          if (result.error) {
            this.callbacks.onError?.(result.error)
          }
          break
          
        case 'session_stopped':
          this.callbacks.onSessionStopped?.()
          break
          
        default:
          console.warn('Unknown speech result type:', result.type)
      }
    } catch (error) {
      console.error('Error parsing speech result:', error)
    }
  }

  /**
   * Schedule reconnection attempt
   */
  private scheduleReconnect() {
    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1) // Exponential backoff
    
    console.log(`Scheduling reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`)
    
    setTimeout(() => {
      if (this.websocket?.readyState !== WebSocket.OPEN) {
        console.log('Attempting to reconnect to speech service...')
        this.connect().catch(error => {
          console.error('Reconnection failed:', error)
        })
      }
    }, delay)
  }

  /**
   * Clean up resources
   */
  private cleanup() {
    this.websocket = null
    this.sessionId = null
    this.isConnecting = false
  }
}

// Create singleton instance
export const speechService = new SpeechService()