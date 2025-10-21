/**
 * Audio processing utilities for speech recognition
 * Handles microphone access, audio formatting, and streaming
 */

export interface AudioConfig {
  sampleRate: number
  channels: number
  bitDepth: number
}

export interface AudioProcessorCallbacks {
  onAudioData?: (audioData: ArrayBuffer) => void
  onError?: (error: string) => void
  onVolumeLevel?: (level: number) => void
}

export class AudioProcessor {
  private mediaRecorder: MediaRecorder | null = null
  private audioContext: AudioContext | null = null
  private analyser: AnalyserNode | null = null
  private microphone: MediaStreamAudioSourceNode | null = null
  private processor: ScriptProcessorNode | null = null
  private stream: MediaStream | null = null
  private callbacks: AudioProcessorCallbacks = {}
  private isRecording = false
  private volumeLevelInterval: number | null = null

  private readonly config: AudioConfig = {
    sampleRate: 16000,
    channels: 1,
    bitDepth: 16
  }

  /**
   * Set callbacks for audio events
   */
  setCallbacks(callbacks: AudioProcessorCallbacks) {
    this.callbacks = { ...this.callbacks, ...callbacks }
  }

  /**
   * Request microphone access and start audio processing
   */
  async startRecording(): Promise<boolean> {
    if (this.isRecording) {
      console.log('Already recording')
      return true
    }

    try {
      // Request microphone access
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: this.config.sampleRate,
          channelCount: this.config.channels,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      })

      // Create audio context
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: this.config.sampleRate
      })

      // Create analyser for volume levels
      this.analyser = this.audioContext.createAnalyser()
      this.analyser.fftSize = 256
      this.analyser.smoothingTimeConstant = 0.8

      // Create microphone source
      this.microphone = this.audioContext.createMediaStreamSource(this.stream)
      this.microphone.connect(this.analyser)

      // Create processor for audio data
      this.processor = this.audioContext.createScriptProcessor(4096, 1, 1)
      this.processor.onaudioprocess = (event) => {
        if (this.isRecording) {
          this.processAudioData(event.inputBuffer)
        }
      }

      this.microphone.connect(this.processor)
      this.processor.connect(this.audioContext.destination)

      this.isRecording = true

      // Start volume level monitoring
      this.startVolumeLevelMonitoring()

      console.log('Audio recording started')
      return true

    } catch (error) {
      console.error('Error starting audio recording:', error)
      this.callbacks.onError?.(`Failed to access microphone: ${error}`)
      return false
    }
  }

  /**
   * Stop audio recording and release resources
   */
  stopRecording() {
    if (!this.isRecording) {
      return
    }

    this.isRecording = false

    // Stop volume monitoring
    if (this.volumeLevelInterval) {
      clearInterval(this.volumeLevelInterval)
      this.volumeLevelInterval = null
    }

    // Stop media recorder
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop()
    }

    // Disconnect audio nodes
    if (this.processor) {
      this.processor.disconnect()
      this.processor = null
    }

    if (this.microphone) {
      this.microphone.disconnect()
      this.microphone = null
    }

    if (this.analyser) {
      this.analyser.disconnect()
      this.analyser = null
    }

    // Close audio context
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close()
      this.audioContext = null
    }

    // Stop media stream
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop())
      this.stream = null
    }

    console.log('Audio recording stopped')
  }

  /**
   * Check if microphone access is available
   */
  async checkMicrophoneAccess(): Promise<boolean> {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices()
      const audioInputs = devices.filter(device => device.kind === 'audioinput')
      return audioInputs.length > 0
    } catch (error) {
      console.error('Error checking microphone access:', error)
      return false
    }
  }

  /**
   * Get current recording state
   */
  getRecordingState(): boolean {
    return this.isRecording
  }

  /**
   * Process audio data and convert to the required format
   */
  private processAudioData(inputBuffer: AudioBuffer) {
    if (!this.isRecording) return

    try {
      // Get audio data from the first channel
      const inputData = inputBuffer.getChannelData(0)
      
      // Convert float32 to int16 (PCM 16-bit)
      const outputBuffer = new ArrayBuffer(inputData.length * 2)
      const outputView = new DataView(outputBuffer)
      
      for (let i = 0; i < inputData.length; i++) {
        // Convert from [-1, 1] to [-32768, 32767]
        const sample = Math.max(-1, Math.min(1, inputData[i]))
        const intSample = Math.round(sample * 32767)
        outputView.setInt16(i * 2, intSample, true) // little-endian
      }

      // Send processed audio data
      this.callbacks.onAudioData?.(outputBuffer)

    } catch (error) {
      console.error('Error processing audio data:', error)
      this.callbacks.onError?.(`Audio processing error: ${error}`)
    }
  }

  /**
   * Start monitoring volume levels
   */
  private startVolumeLevelMonitoring() {
    if (!this.analyser) return

    const dataArray = new Uint8Array(this.analyser.frequencyBinCount)

    this.volumeLevelInterval = window.setInterval(() => {
      if (!this.analyser || !this.isRecording) return

      this.analyser.getByteFrequencyData(dataArray)
      
      // Calculate average volume level
      let sum = 0
      for (let i = 0; i < dataArray.length; i++) {
        sum += dataArray[i]
      }
      
      const averageLevel = sum / dataArray.length
      const normalizedLevel = averageLevel / 255 // Normalize to 0-1
      
      this.callbacks.onVolumeLevel?.(normalizedLevel)
    }, 100) // Update every 100ms
  }

  /**
   * Convert audio blob to required format (for alternative implementation)
   */
  static async convertAudioBlob(blob: Blob): Promise<ArrayBuffer> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => {
        if (reader.result instanceof ArrayBuffer) {
          resolve(reader.result)
        } else {
          reject(new Error('Failed to read audio blob'))
        }
      }
      reader.onerror = () => reject(reader.error)
      reader.readAsArrayBuffer(blob)
    })
  }

  /**
   * Check browser compatibility for audio recording
   */
  static checkBrowserSupport(): {
    supported: boolean
    missing: string[]
  } {
    const missing: string[] = []

    if (!navigator.mediaDevices?.getUserMedia) {
      missing.push('MediaDevices.getUserMedia')
    }

    if (!window.AudioContext && !(window as any).webkitAudioContext) {
      missing.push('AudioContext')
    }

    if (!window.MediaRecorder) {
      missing.push('MediaRecorder')
    }

    return {
      supported: missing.length === 0,
      missing
    }
  }
}

// Create singleton instance
export const audioProcessor = new AudioProcessor()