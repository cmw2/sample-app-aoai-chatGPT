import { useContext, useEffect, useRef, useState } from 'react'
import { FontIcon, Stack, Text } from '@fluentui/react'
import { MicRegular, MicOffRegular, ErrorCircleRegular } from '@fluentui/react-icons'

import styles from './SpeechInput.module.css'
import { speechService, SpeechConfig } from '../../api/speechService'
import { audioProcessor, AudioProcessor } from '../../utils/audioProcessor'
import { AppStateContext } from '../../state/AppProvider'

interface Props {
  onTranscription: (text: string, isFinal: boolean) => void
  onError?: (error: string) => void
  disabled?: boolean
  mode?: 'push-to-talk' | 'continuous'
}

export const SpeechInput = ({ onTranscription, onError, disabled = false, mode = 'push-to-talk' }: Props) => {
  const [isRecording, setIsRecording] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [connectionState, setConnectionState] = useState<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected')
  const [speechConfig, setSpeechConfig] = useState<SpeechConfig | null>(null)
  const [volumeLevel, setVolumeLevel] = useState(0)
  const [transcriptionText, setTranscriptionText] = useState('')
  const [error, setError] = useState<string | null>(null)
  
  const appStateContext = useContext(AppStateContext)
  const speechEnabled = appStateContext?.state.frontendSettings?.speech_enabled || false
  
  // Refs for managing state during cleanup
  const isRecordingRef = useRef(false)
  const connectionStateRef = useRef<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected')

  useEffect(() => {
    if (!speechEnabled) return

    // Initialize speech service
    initializeSpeechService()

    return () => {
      cleanup()
    }
  }, [speechEnabled])

  useEffect(() => {
    isRecordingRef.current = isRecording
  }, [isRecording])

  useEffect(() => {
    connectionStateRef.current = connectionState
  }, [connectionState])

  const initializeSpeechService = async () => {
    try {
      // Check browser support
      const browserSupport = AudioProcessor.checkBrowserSupport()
      if (!browserSupport.supported) {
        const errorMsg = `Browser not supported. Missing: ${browserSupport.missing.join(', ')}`
        setError(errorMsg)
        onError?.(errorMsg)
        return
      }

      // Get speech configuration
      const config = await speechService.getConfig()
      if (!config || !config.enabled) {
        const errorMsg = 'Speech service not available'
        setError(errorMsg)
        onError?.(errorMsg)
        return
      }

      setSpeechConfig(config)

      // Set up speech service callbacks
      speechService.setCallbacks({
        onRecognizing: (text: string) => {
          setTranscriptionText(text)
          onTranscription(text, false)
        },
        onRecognized: (text: string, confidence: number) => {
          setTranscriptionText(text)
          onTranscription(text, true)
          console.log(`Speech recognized: "${text}" (confidence: ${confidence})`)
        },
        onError: (error: string) => {
          console.error('Speech service error:', error)
          setError(error)
          onError?.(error)
          stopRecording()
        },
        onSessionStarted: () => {
          console.log('Speech session started')
        },
        onSessionStopped: () => {
          console.log('Speech session stopped')
          setIsRecording(false)
        },
        onConnectionStateChange: (state) => {
          setConnectionState(state)
          if (state === 'error') {
            stopRecording()
          }
        }
      })

      // Set up audio processor callbacks
      audioProcessor.setCallbacks({
        onAudioData: (audioData: ArrayBuffer) => {
          if (connectionStateRef.current === 'connected' && isRecordingRef.current) {
            speechService.sendAudioData(audioData)
          }
        },
        onError: (error: string) => {
          console.error('Audio processor error:', error)
          setError(error)
          onError?.(error)
          stopRecording()
        },
        onVolumeLevel: (level: number) => {
          setVolumeLevel(level)
        }
      })

    } catch (error) {
      console.error('Failed to initialize speech service:', error)
      setError(String(error))
      onError?.(String(error))
    }
  }

  const startRecording = async () => {
    if (disabled || isRecording || !speechConfig) return

    setIsConnecting(true)
    setError(null)
    setTranscriptionText('')

    try {
      // Connect to speech service
      const connected = await speechService.connect()
      if (!connected) {
        throw new Error('Failed to connect to speech service')
      }

      // Start audio recording
      const recordingStarted = await audioProcessor.startRecording()
      if (!recordingStarted) {
        throw new Error('Failed to start audio recording')
      }

      setIsRecording(true)
      console.log('Speech recording started')

    } catch (error) {
      console.error('Error starting recording:', error)
      setError(String(error))
      onError?.(String(error))
    } finally {
      setIsConnecting(false)
    }
  }

  const stopRecording = () => {
    if (!isRecording) return

    try {
      // Stop audio recording
      audioProcessor.stopRecording()

      // Stop speech recognition
      speechService.stopRecognition()

      setIsRecording(false)
      setVolumeLevel(0)
      console.log('Speech recording stopped')

    } catch (error) {
      console.error('Error stopping recording:', error)
      setError(String(error))
      onError?.(String(error))
    }
  }

  const toggleRecording = () => {
    if (isRecording) {
      stopRecording()
    } else {
      startRecording()
    }
  }

  const cleanup = () => {
    if (isRecordingRef.current) {
      audioProcessor.stopRecording()
    }
    speechService.disconnect()
  }

  // Don't render if speech is not enabled
  if (!speechEnabled) {
    return null
  }

  const getMicrophoneIcon = () => {
    if (error) {
      return <ErrorCircleRegular className={styles.microphoneIconError} />
    }
    if (isRecording) {
      return <MicRegular className={styles.microphoneIconRecording} />
    }
    return <MicOffRegular className={styles.microphoneIcon} />
  }

  const getMicrophoneButtonClass = () => {
    if (disabled || isConnecting) {
      return styles.microphoneButtonDisabled
    }
    if (error) {
      return styles.microphoneButtonError
    }
    if (isRecording) {
      return styles.microphoneButtonRecording
    }
    return styles.microphoneButton
  }

  return (
    <Stack className={styles.speechInputContainer}>
      <div
        className={getMicrophoneButtonClass()}
        role="button"
        tabIndex={0}
        aria-label={isRecording ? 'Stop recording' : 'Start recording'}
        onClick={toggleRecording}
        onKeyDown={e => (e.key === 'Enter' || e.key === ' ' ? toggleRecording() : null)}
        title={error || (isRecording ? 'Stop recording' : 'Start recording')}
      >
        {getMicrophoneIcon()}
        
        {/* Volume level indicator */}
        {isRecording && (
          <div className={styles.volumeLevelContainer}>
            <div 
              className={styles.volumeLevel}
              style={{ width: `${Math.min(volumeLevel * 100, 100)}%` }}
            />
          </div>
        )}
        
        {/* Connection state indicator */}
        {isConnecting && (
          <div className={styles.connectingIndicator}>
            <div className={styles.spinner} />
          </div>
        )}
      </div>

      {/* Live transcription display */}
      {transcriptionText && (
        <div className={styles.transcriptionContainer}>
          <Text variant="small" className={styles.transcriptionText}>
            {transcriptionText}
          </Text>
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className={styles.errorContainer}>
          <Text variant="small" className={styles.errorText}>
            {error}
          </Text>
        </div>
      )}

      {/* Speech config info (debug) */}
      {speechConfig && import.meta.env.DEV && (
        <div className={styles.debugInfo}>
          <Text variant="tiny">
            Lang: {speechConfig.language} | Region: {speechConfig.region} | State: {connectionState}
          </Text>
        </div>
      )}
    </Stack>
  )
}