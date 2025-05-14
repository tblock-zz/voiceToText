import tkinter as tk
from tkinter import scrolledtext, messagebox
import sounddevice
import speech_recognition as sr
from deepmultilingualpunctuation import PunctuationModel
import threading
import queue
import time
import getpass
import os
import pyperclip # Für die Zwischenablage
import keyboard  # Für globale Tasten-Events
#-------------------------------------------------------------------------------
# --- Konstanten ---
SAMPLE_RATE = 16000
CHANNELS = 1
DEVICE_INDEX = None
AUDIO_FORMAT_WIDTH = 2

# default is german
langSelector = "de" 

lang = {
    "de": {
        "start": "Aufnahme starten",
        "stop": "Aufnahme stoppen",
        "clr": "Text löschen",
        "save": "Speichern",
        "info1": "Bereit. Shift gedrückt halten zum Aufnehmen oder Button benutzen.",
        "info2": "Globale Hotkeys (Shift, Strg+C) aktiv.",
        "punct_model_loading": "loading Punctuation model...",
        "punct_model_loaded": "Punctuation model loaded.",
        "punct_model_failed": "Interpunktionsmodell konnte nicht geladen werden: {e}\nDie Interpunktion wird ggf. fehlen.",
        "recording_error": "Fehler beim Starten der Aufnahme: {e}",
        "recording_failed": "Konnte Audioaufnahme nicht starten: {e}",
        "recording_stop_error": "Fehler beim Stoppen des Streams: {e}",
        "deviceCheckError": "Fehler bei Audio-Geräteprüfung:",
        "recording_stopped": "Aufnahme gestoppt. Verarbeite Audio...",
        "ready": "Bereit.",
        "recording_shift": "Aufnahme via Shift gestartet...",
        "recording_running": "Aufnahme läuft...",
        "audio_stream_status": "Audio Stream Status: {status}",
        "text_deleted": "Text gelöscht.",
        "file_save_error": "Fehler beim Speichern der Datei: {e}",
        "save_started": "Speichern gestartet. Ziel: '{filename}'",
        "save_stopped": "Speichern beendet.",
        "save_file_created": "Speichern in '{filename}' beendet.",
        "save_file_create_error": "Fehler beim Erstellen der Speicherdatei: {e}",
        "clipboard_error": "Fehler beim Kopieren: {e}",
        "clipboard_success": "Text in Zwischenablage kopiert.",
        "clipboard_empty": "Kein Text zum Kopieren vorhanden.",
        "close_confirm": "Möchten Sie die Anwendung wirklich beenden?",
        "closing": "Anwendung wird beendet...",
        "audio_device_error": "Audio Fehler",
        "audio_device_not_found": "Kein Audio-Eingabegerät gefunden. Anwendung kann nicht starten.",
        "audio_device_init_error": "Fehler bei Audiogeräte-Init.: {e}\nStellen Sie sicher, dass ein Mikrofon angeschlossen ist.",
        "stt_thread_error": "STT Thread Fehler: {e}",
        "recognition_error": "Sprache nicht verstanden.",
        "api_error": "API Fehler: {e}",
        "api_unreachable": "Service nicht erreichbar: {e}",
        "unexpected_stt_error": "Unerwarteter STT Fehler: {e}",
        "unexpected_recognizeAndDisplay_error": "Unerwarteter Fehler in recognizeAndDisplay: {e}",
        "hotkey_error": "Fehler beim Setzen der globalen Hotkeys: {e}. Shift/Strg+C funktionieren evtl. nicht global.",
        "hotkey_error_box": "Globale Hotkeys konnten nicht registriert werden: {e}",
        "save_stop": "Speichern Stoppen",
        "save_start": "Speichern Starten",
        "record_stop": "Aufnahme stoppen",
        "record_start": "Aufnahme starten",
        "errorProcessAudioQueue": "Fehler in processAudioQueue: {e}",
        "transcribe": "Transkribiere Audio...",
    },
    "en": {
      "start": "Start recording",
      "stop": "Stop recording",
      "clr": "Clear text",
      "save": "Save",
      "info1": "Ready. Hold Shift to record or use the button.",
      "info2": "Global hotkeys (Shift, Ctrl+C) active.",
      "punct_model_loading": "Loading punctuation model...",
      "punct_model_loaded": "Punctuation model loaded.",
      "punct_model_failed": "Could not load punctuation model: {e}\nPunctuation may be missing.",
      "recording_error": "Error starting recording: {e}",
      "recording_failed": "Could not start audio recording: {e}",
      "recording_stop_error": "Error stopping the stream: {e}",
      "deviceCheckError": "Error checking audio devices:",
      "recording_stopped": "Recording stopped. Processing audio...",
      "ready": "Ready.",
      "recording_shift": "Recording started via Shift...",
      "recording_running": "Recording in progress...",
      "audio_stream_status": "Audio stream status: {status}",
      "text_deleted": "Text deleted.",
      "file_save_error": "Error saving file: {e}",
      "save_started": "Saving started. Target: '{filename}'",
      "save_stopped": "Saving stopped.",
      "save_file_created": "Saving to '{filename}' finished.",
      "save_file_create_error": "Error creating save file: {e}",
      "clipboard_error": "Error copying: {e}",
      "clipboard_success": "Text copied to clipboard.",
      "clipboard_empty": "No text to copy.",
      "close_confirm": "Do you really want to exit the application?",
      "closing": "Application is closing...",
      "audio_device_error": "Audio error",
      "audio_device_not_found": "No audio input device found. Application cannot start.",
      "audio_device_init_error": "Error initializing audio device: {e}\nPlease make sure a microphone is connected.",
      "stt_thread_error": "STT thread error: {e}",
      "recognition_error": "Could not understand speech.",
      "api_error": "API error: {e}",
      "api_unreachable": "Service not reachable: {e}",
      "unexpected_stt_error": "Unexpected STT error: {e}",
      "unexpected_recognizeAndDisplay_error": "Unexpected error in recognizeAndDisplay: {e}",
      "hotkey_error": "Error setting global hotkeys: {e}. Shift/Ctrl+C may not work globally.",
      "hotkey_error_box": "Global hotkeys could not be registered: {e}",
      "save_stop": "Stop saving",
      "save_start": "Start saving",
      "record_stop": "Stop recording",
      "record_start": "Start recording",
      "errorProcessAudioQueue": "Error in processAudioQueue: {e}",
      "transcribe": "Transcribing audio...",
    },
} 
#-------------------------------------------------------------------------------
class SpeechToTextApp:
  def __init__(self, rootWindow):
    self.root = rootWindow
    self.root.title("Audio zu Text Streamer")
    self.root.geometry("700x550")

    self.isRecording = False
    self.audioQueue = queue.Queue()
    self.recognizer = sr.Recognizer()
    self.speechRecognitionThread = None
    self.recordingStream = None
    self.textBuffer = []

    self.isSavingToFile = False
    self.currentSaveFilename = None

    self.punctuationModel = None
    try:
      print(lang[langSelector]["punct_model_loading"], flush=True)
      # Modell beim Start laden, damit es nicht bei jeder Erkennung neu geladen wird
      self.punctuationModel = PunctuationModel(model="oliverguhr/fullstop-punctuation-multilang-large")
      print(lang[langSelector]["punct_model_loaded"], flush=True)
    except Exception as e:
      print(f"Could not load punctuation model: {e}", flush=True)
      messagebox.showwarning("Interpunktion", lang[langSelector]["punct_model_failed"].format(e=e))

    self.setupGui()
    self.root.bind('<KeyPress-Shift_L>', lambda e: self.handleShiftPress())
    self.root.bind('<KeyRelease-Shift_L>', lambda e: self.handleShiftRelease())    
    self.setupKeyboardHooks()

    self.root.protocol("WM_DELETE_WINDOW", self.onClosing)
  #-------------------------------------------------------------------------------
  def setupGui(self):
    self.textDisplay = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, state=tk.DISABLED, height=20, width=80)
    self.textDisplay.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

    buttonFrame = tk.Frame(self.root)
    buttonFrame.pack(pady=5)

    self.recordButton = tk.Button(buttonFrame, text=lang[langSelector]["record_start"], command=self.toggleRecordingButton)
    self.recordButton.pack(side=tk.LEFT, padx=5)

    self.clearButton = tk.Button(buttonFrame, text=lang[langSelector]["clr"], command=self.clearDisplayedText)
    self.clearButton.pack(side=tk.LEFT, padx=5)

    self.saveModeButton = tk.Button(buttonFrame, text=lang[langSelector]["save_start"], command=self.toggleSaveMode)
    self.saveModeButton.pack(side=tk.LEFT, padx=5)
    
    self.statusLabel = tk.Label(self.root, text=lang[langSelector]["info1"])
    self.statusLabel.pack(pady=5)
  #-------------------------------------------------------------------------------
  def setupKeyboardHooks(self):
    try:
      keyboard.add_hotkey('ctrl+c', self.copyTextToClipboard, suppress=False)
      self.updateStatus(lang[langSelector]["info2"])
    except Exception as e:
      self.updateStatus(lang[langSelector]["hotkey_error"].format(e=e))
      messagebox.showerror("Hotkey Fehler", lang[langSelector]["hotkey_error_box"].format(e=e))
  #-------------------------------------------------------------------------------
  def updateStatus(self, message):
    self.statusLabel.config(text=message)
    self.root.update_idletasks()
  #-------------------------------------------------------------------------------
  def appendTextToDisplay(self, newText):
    if not newText:
      return
    
    self.textBuffer.append(newText)
    self.textDisplay.config(state=tk.NORMAL)
    self.textDisplay.insert(tk.END, newText + "\n")
    self.textDisplay.see(tk.END)
    self.textDisplay.config(state=tk.DISABLED)
    
    if self.isSavingToFile and self.currentSaveFilename:
      self.saveBufferedTextToFile()
  #-------------------------------------------------------------------------------
  def audioCallback(self, indata, frames, timeInfo, status):
    if status:
      print(f"Audio Stream Status: {status}", flush=True)
    self.audioQueue.put(bytes(indata))
  #-------------------------------------------------------------------------------
  def _startAudioStreamInternal(self):
    """Startet den Audiostream und den Verarbeitungsthread, wenn nötig."""
    if self.recordingStream: 
        return True
  #-------------------------------------------------------------------------------
    try:
      self.recordingStream = sounddevice.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        callback=self.audioCallback,
        device=DEVICE_INDEX,
        dtype='int16'
      )
      self.recordingStream.start()
      
      if self.speechRecognitionThread is None or not self.speechRecognitionThread.is_alive():
        self.speechRecognitionThread = threading.Thread(target=self.processAudioQueue, daemon=True)
        self.speechRecognitionThread.start()
        self.recordButton.config(text=lang[langSelector]["record_stop"])

        self.isRecording = True
      return True
    except Exception as e:
      self.updateStatus(lang[langSelector]["recording_error"].format(e=e))
      messagebox.showerror(lang[langSelector]["audio_device_error"], lang[langSelector]["recording_failed"].format(e=e))
      if self.recordingStream:
        try: 
          self.recordingStream.stop() 
          self.recordingStream.close()
        except Exception: 
           pass
        self.recordingStream = None
      return False
  #-------------------------------------------------------------------------------
  def _stopAudioStreamInternalAndProcess(self):
    """Stoppt den Audiostream (falls aktiv) und sendet Signal zur Verarbeitung."""
    if self.recordingStream:
      try:
        self.recordingStream.stop()
        self.recordingStream.close()
        self.recordingStream = None
      except Exception as e:
        self.updateStatus(lang[langSelector]["recording_stop_error"].format(e=e))
    
    self.isRecording = False
    self.recordButton.config(text=lang[langSelector]["record_start"])
    self.updateStatus(lang[langSelector]["recording_stopped"])
    self.audioQueue.put("END_OF_STREAM_MARKER")
  #-------------------------------------------------------------------------------
  def handleShiftPress(self):
    if not self.recordingStream:
      if self._startAudioStreamInternal():
        self.updateStatus(lang[langSelector]["recording_shift"])
  #-------------------------------------------------------------------------------
  def handleShiftRelease(self):
    if self.recordingStream:
      self._stopAudioStreamInternalAndProcess()
  #-------------------------------------------------------------------------------
  def toggleRecordingButton(self):
    if self.recordingStream:
      self._stopAudioStreamInternalAndProcess()
      self.recordButton.config(text=lang[langSelector]["record_start"])
    else:  
      if self._startAudioStreamInternal():
        self.recordButton.config(text=lang[langSelector]["record_stop"])
  #-------------------------------------------------------------------------------
  def processAudioQueue(self):
    tempAudioFrames = []
    while True:
        try:
            audioChunk = self.audioQueue.get(timeout=0.2)
            
            if audioChunk == "END_OF_STREAM_MARKER":
                if tempAudioFrames:
                    # Kopie der Frames übergeben, da tempAudioFrames sofort geleert wird
                    framesToProcess = b''.join(tempAudioFrames)
                    tempAudioFrames = [] 
                    self.recognizeAndDisplay(framesToProcess) 
                else: 
                    if not (self.recordingStream):
                         self.root.after(0, lambda: self.updateStatus(lang[langSelector]["ready"]))
                continue

            if audioChunk is None: 
                if tempAudioFrames: 
                     self.recognizeAndDisplay(b''.join(tempAudioFrames))
                break

            tempAudioFrames.append(audioChunk)

        except queue.Empty:
            if not (self.recordingStream) and tempAudioFrames:
                framesToProcess = b''.join(tempAudioFrames)
                tempAudioFrames = []
                self.recognizeAndDisplay(framesToProcess)
                self.root.after(0, lambda: self.updateStatus(lang[langSelector]["ready"])) # Sicherstellen, dass Status "Bereit" ist
            continue
        except Exception as e:
            print(lang[langSelector]["errorProcessAudioQueue"].format(e=e), flush=True)
            self.root.after(0, lambda: self.updateStatus(lang[langSelector]["stt_thread_error"].format(e=e)))
            tempAudioFrames = [] # Reset
  #-------------------------------------------------------------------------------
  def recognizeAndDisplay(self, audioBytes):
    if not audioBytes:
        if not (self.recordingStream): 
             self.root.after(0, lambda: self.updateStatus(lang[langSelector]["ready"]))
        return

    self.root.after(0, lambda: self.updateStatus(lang[langSelector]["transcribe"]))
    try:
      audioData = sr.AudioData(audioBytes, SAMPLE_RATE, AUDIO_FORMAT_WIDTH)
      raw_text = self.recognizer.recognize_google(audioData, language="de-DE")
      
      processed_text = raw_text 

      if raw_text and self.punctuationModel:
        try:
            processed_text = self.punctuationModel.restore_punctuation(raw_text)
        except Exception as e:
            print(f"Error applying punctuation model: {e}", flush=True)
      
      if processed_text: 
        if processed_text.strip(): 
            processed_text = processed_text.strip()
            processed_text = processed_text[0].upper() + processed_text[1:]

        self.root.after(0, lambda t=processed_text: self.appendTextToDisplay(t))
      
      if not (self.isRecording):
        self.root.after(0, lambda: self.updateStatus(lang[langSelector]["ready"]))
      elif self.isRecording:
        self.root.after(0, lambda m=currentMode: self.updateStatus(lang[langSelector]["recording_running"]))

    except sr.UnknownValueError:
      self.root.after(0, lambda: self.updateStatus(lang[langSelector]["recognition_error"]))
      if not (self.isRecording):
        self.root.after(0, lambda: self.updateStatus(lang[langSelector]["ready"]))
    except sr.RequestError as e:
      self.root.after(0, lambda: self.updateStatus(lang[langSelector]["api_error"].format(e=e)))
      self.root.after(0, lambda e=e: messagebox.showerror(lang[langSelector]["api_error"], lang[langSelector]["api_unreachable"].format(e=e)))
      if not (self.isRecording):
        self.root.after(0, lambda: self.updateStatus(lang[langSelector]["ready"]))
    except Exception as e:
      self.root.after(0, lambda: self.updateStatus(lang[langSelector]["unexpected_stt_error"].format(e=e)))
      print( self.updateStatus(lang[langSelector]["unexpected_recognizeAndDisplay_error"].format(e=e)), flush=True)
      if not (self.isRecording):
        self.root.after(0, lambda: self.updateStatus(lang[langSelector]["ready"]))
  #-------------------------------------------------------------------------------
  def clearDisplayedText(self):
    self.textDisplay.config(state=tk.NORMAL)
    self.textDisplay.delete(1.0, tk.END)
    self.textDisplay.config(state=tk.DISABLED)
    self.textBuffer = []
    self.updateStatus(lang[langSelector]["text_deleted"])
    if self.isSavingToFile and self.currentSaveFilename:
        self.saveBufferedTextToFile()
  #-------------------------------------------------------------------------------
  def saveBufferedTextToFile(self):
    if not self.currentSaveFilename:
      return
    try:
      fullText = "\n".join(self.textBuffer)
      with open(self.currentSaveFilename, "w", encoding="utf-8") as f:
        f.write(fullText)
    except Exception as e:
      self.updateStatus(lang[langSelector]["file_save_error"].format(e=e))
  #-------------------------------------------------------------------------------
  def toggleSaveMode(self):
    if self.isSavingToFile:
      self.isSavingToFile = False
      self.saveModeButton.config(text=lang[langSelector]["save_start"])
      if self.currentSaveFilename:
          self.updateStatus(lang[langSelector]["save_file_created"].format(filename=os.path.basename(self.currentSaveFilename)))
      else:
          self.updateStatus(lang[langSelector]["save_stopped"])
    else:
      self.isSavingToFile = True
      try: username = getpass.getuser().replace(" ", "_")
      except Exception: username = "user"
      timestamp = int(time.time())
      filename = f"{username}_{timestamp}_session.txt"
      self.currentSaveFilename = os.path.join(os.getcwd(), filename)
      self.saveModeButton.config(text=lang[langSelector]["save_stop"])
      self.updateStatus(lang[langSelector]["save_started"].format(filename=os.path.basename(self.currentSaveFilename)))
      if self.textBuffer: self.saveBufferedTextToFile()
      else:
          try:
              with open(self.currentSaveFilename, "w", encoding="utf-8") as f: f.write("") 
          except Exception as e:
              self.updateStatus(lang[langSelector]["save_file_create_error"].format(e=e))
              self.isSavingToFile = False
              self.saveModeButton.config(text=lang[langSelector]["save_start"])
  #-------------------------------------------------------------------------------
  def copyTextToClipboard(self):
    textToCopy = "\n".join(self.textBuffer)
    if textToCopy:
      try: pyperclip.copy(textToCopy)
      except pyperclip.PyperclipException as e:
        self.updateStatus(lang[langSelector]["clipboard_error"].format(e=e))
        messagebox.showwarning("Zwischenablage Fehler", lang[langSelector]["clipboard_error"].format(e=e))
      else: self.updateStatus(lang[langSelector]["clipboard_success"])
    else: self.updateStatus(lang[langSelector]["clipboard_empty"])
  #-------------------------------------------------------------------------------
  def onClosing(self):
    if messagebox.askokcancel("Beenden", lang[langSelector]["close_confirm"]):
      self.updateStatus(lang[langSelector]["closing"])
      keyboard.remove_all_hotkeys()
      if self.isRecording:
          if self.recordingStream:
              try: 
                self.recordingStream.stop()
                self.recordingStream.close()
              except Exception: 
                 pass
              self.recordingStream = None
      if self.speechRecognitionThread and self.speechRecognitionThread.is_alive():
          self.audioQueue.put(None) 
          self.speechRecognitionThread.join(timeout=1.0)
      if self.isSavingToFile and self.currentSaveFilename and self.textBuffer:
          self.saveBufferedTextToFile()
          print(f"Letzter Text in {os.path.basename(self.currentSaveFilename)} gespeichert.", flush=True)
      self.root.destroy()
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  try:
    devices = sounddevice.query_devices()
    defaultInputDevice = None
    default_input_idx = sounddevice.default.device[0]
    if default_input_idx != -1 and devices[default_input_idx]['max_input_channels'] > 0:
        DEVICE_INDEX = default_input_idx
        defaultInputDevice = devices[DEVICE_INDEX]
    else:
        input_devices = [d for d in devices if d.get('max_input_channels', 0) > 0 and d.get('hostapi', -1) != -1]
        if input_devices:
            DEVICE_INDEX = input_devices[0]['index']
            defaultInputDevice = input_devices[0]
        else:
            messagebox.showerror(lang[langSelector]["audio_device_error"], lang[langSelector]["audio_device_not_found"])
            exit()
  except Exception as e:
      messagebox.showerror(lang[langSelector]["audio_device_error"], lang[langSelector]["audio_device_init_error"].format(e=e))
      print(lang[langSelector]["deviceCheckError"]+f"{e}", flush=True)
      DEVICE_INDEX = None # Fallback sounddevice default

  mainRoot = tk.Tk()
  app = SpeechToTextApp(mainRoot)
  mainRoot.mainloop()