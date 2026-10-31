/* SonicAgent Voice Studio. No frameworks, analytics, or persistent tokens. */
(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  var E = {};
  [
    "liveDot","liveStatus","readyDot","readyStatus","ttsDot","ttsStatus",
    "connectionDot","connectionText","refreshBtn","guestModeBtn","tokenModeBtn",
    "accessHint","keyField","tokenInput","toggleTokenBtn","recordTab","uploadTab",
    "recordPane","uploadPane","recordBtn","recordTime","recordHint","waveCanvas",
    "audioInput","dropZone","uploadTitle","uploadSubtitle","audioPreview",
    "audioFileName","audioFileSize","removeAudioBtn","languageSelect","transcribeBtn",
    "transcriptText","resultMeta","copyBtn","ttsInput","charCounter",
    "ttsLanguage","ttsVoice","synthesizeBtn","audioResultTitle",
    "audioResultSubtitle","audioPlayer","ttsNotice","toast"
  ].forEach(function (id) { E[id] = $(id); });
  var S = {
    mode:"token", token:"", demoEnabled:false, demoTts:false, demoSeconds:8,
    demoBytes:1200000, limitBytes:2097152, limitSeconds:15,
    recording:false, busy:false, recorder:null, stream:null, chunks:[],
    file:null, transcript:"", audioUrl:null, start:0, timer:null, toastTimer:null,
    audioCtx:null, analyser:null, microphoneNode:null, ready:false,
    ttsReady:false, ttsKnown:false, raf:null
  };
  function notify(text,isError) {
    E.toast.textContent = String(text);
    E.toast.classList.toggle("error",!!isError);
    E.toast.classList.add("show");
    clearTimeout(S.toastTimer);
    S.toastTimer = setTimeout(function(){E.toast.classList.remove("show");},4500);
  }
  function indicator(dot,label,value,kind) {
    dot.className = "status-dot " + (kind || "");
    label.textContent = value;
  }
  function fmtBytes(n) {
    return n < 1024 ? n + " B" : n < 1048576 ? (n/1024).toFixed(1) + " KB" : (n/1048576).toFixed(2)+" MB";
  }
  function authenticated() { return S.mode === "demo" ? S.demoEnabled : !!S.token.trim(); }
  function headers() { return S.mode === "demo" ? {"X-Sonic-Demo-UI":"1"} : {"Authorization":"Bearer "+S.token.trim()}; }
  function updateButtons() {
    E.transcribeBtn.disabled = !authenticated() || !S.file || S.busy || S.recording;
    E.synthesizeBtn.disabled = !authenticated() || !E.ttsInput.value.trim() || S.busy || !S.ttsReady || (S.mode === "demo" && !S.demoTts);
    E.recordBtn.disabled = S.busy && !S.recording;
    if (!S.ttsReady) E.ttsNotice.textContent = "Piper is not available on this server. Install and enable a voice model to use TTS.";
    else if (S.mode === "demo" && !S.demoTts) E.ttsNotice.textContent = "The Space owner has disabled public voice synthesis; owner testing remains available.";
    else E.ttsNotice.textContent = voiceNotice();
  }
  function request(path,opts,ms) {
    var controller = new AbortController();
    var timer = setTimeout(function(){controller.abort();},ms || 12000);
    return fetch(path,Object.assign({cache:"no-store",signal:controller.signal},opts || {}))
      .finally(function(){clearTimeout(timer);});
  }
  async function json(path,opts) {
    var response = await request(path,opts,12000);
    var data = await response.json().catch(function(){return {};});
    if (!response.ok) throw new Error((data.error && data.error.message) || data.detail || "HTTP " + response.status);
    return data;
  }
  async function errorMessage(response) {
    var data = await response.json().catch(function(){return {};});
    return (data.error && data.error.message) || data.detail || data.message || "HTTP " + response.status;
  }
  async function status() {
    E.refreshBtn.disabled = true;
    try {
      var results = await Promise.allSettled([json("/health/live"),json("/health/ready")]);
      var online = results[0].status === "fulfilled";
      var ready = results[1].status === "fulfilled" ? results[1].value : {};
      S.ready = ready.ready === true;
      S.ttsKnown = !!ready.tts;
      S.ttsReady = ready.tts && ready.tts.ready === true;
      indicator(E.liveDot,E.liveStatus,online?"Online":"Offline",online?"ok":"error");
      indicator(E.readyDot,E.readyStatus,S.ready?"Ready":online?"Warming up":"Unavailable",S.ready?"ok":online?"wait":"error");
      indicator(E.ttsDot,E.ttsStatus,S.ttsReady?"Ready":ready.tts && ready.tts.available?"Not loaded":"Disabled",S.ttsReady?"ok":"wait");
      E.connectionDot.className = "dot " + (online?"ok":"error");
      E.connectionText.textContent = online?"Service online":"Service unavailable";
      updateButtons();
    } finally {E.refreshBtn.disabled = false;}
  }
  async function getDemo() {
    try {
      var d = await json("/demo/status");
      S.demoEnabled = d.enabled === true;
      S.demoTts = d.tts_enabled === true;
      if (Number.isFinite(d.max_audio_seconds)) S.demoSeconds = d.max_audio_seconds;
      if (Number.isFinite(d.max_upload_bytes)) S.demoBytes = d.max_upload_bytes;
    } catch (_) {S.demoEnabled=false;}
    E.guestModeBtn.disabled = !S.demoEnabled;
    E.guestModeBtn.title = S.demoEnabled ? "Try the limited public demo" : "The owner has not enabled anonymous inference";
    setMode(S.demoEnabled?"demo":"token");
  }
  async function capabilities() {
    if (S.mode !== "token" || !S.token.trim()) return;
    try {
      var c = await json("/v1/audio/capabilities",{headers:headers()});
      if (c.stt && c.stt.max_upload_bytes) S.limitBytes = c.stt.max_upload_bytes;
      if (c.stt && c.stt.max_seconds) S.limitSeconds = c.stt.max_seconds;
      S.ttsReady = !!(c.tts && c.tts.ready === true);
      indicator(E.ttsDot,E.ttsStatus,S.ttsReady?"Ready":"Disabled",S.ttsReady?"ok":"wait");
      updateButtons();
    } catch (err) {notify("Capabilities: "+err.message,true);}
  }
  function setMode(mode) {
    if (mode === "demo" && !S.demoEnabled) return;
    S.mode = mode;
    E.guestModeBtn.classList.toggle("selected",mode === "demo");
    E.tokenModeBtn.classList.toggle("selected",mode === "token");
    E.guestModeBtn.setAttribute("aria-pressed",String(mode === "demo"));
    E.tokenModeBtn.setAttribute("aria-pressed",String(mode === "token"));
    E.keyField.hidden = mode === "demo";
    E.ttsInput.maxLength = mode === "demo" ? 180 : 500;
    E.charCounter.textContent = E.ttsInput.value.length+" / "+E.ttsInput.maxLength;
    E.accessHint.textContent = mode === "demo"
      ? "Public demo: limited recordings are sent to this server for inference. No API token required."
      : "Owner/testing mode: enter a token. It stays in this tab memory and is never stored.";
    if(mode === "token" && S.token.trim()) capabilities();
    updateButtons();
  }
  E.guestModeBtn.addEventListener("click",function(){setMode("demo");});
  E.tokenModeBtn.addEventListener("click",function(){setMode("token");});
  var keyDebounce;
  E.tokenInput.addEventListener("input",function(){
    S.token = E.tokenInput.value;
    clearTimeout(keyDebounce);
    updateButtons();
    if(S.token.trim()) keyDebounce=setTimeout(capabilities,600);
  });
  E.toggleTokenBtn.addEventListener("click",function(){
    var show=E.tokenInput.type === "password";
    E.tokenInput.type = show ? "text" : "password";
    E.toggleTokenBtn.textContent = show ? "Hide" : "Show";
  });
  E.refreshBtn.addEventListener("click",function(){status();capabilities();});

  function clearFile() {
    S.file = null;
    E.audioPreview.hidden = true;
    E.audioInput.value = "";
    updateButtons();
  }
  function setFile(file) {
    if(!file) return;
    var limit=S.mode === "demo" ? S.demoBytes : S.limitBytes;
    if(file.size > limit) return notify("File exceeds "+fmtBytes(limit)+". Choose a shorter recording.",true);
    if(file.size < 64) return notify("Audio file is empty.",true);
    S.file=file;
    E.audioPreview.hidden=false;
    E.audioFileName.textContent=file.name || "recording.webm";
    E.audioFileSize.textContent=fmtBytes(file.size);
    updateButtons();
  }
  function tab(name) {
    if(S.recording || S.busy) return;
    var recording = name === "record";
    E.recordTab.classList.toggle("active",recording);
    E.uploadTab.classList.toggle("active",!recording);
    E.recordTab.setAttribute("aria-selected",String(recording));
    E.uploadTab.setAttribute("aria-selected",String(!recording));
    E.recordPane.hidden=!recording;
    E.uploadPane.hidden=recording;
    clearFile();
  }
  E.recordTab.addEventListener("click",function(){tab("record");});
  E.uploadTab.addEventListener("click",function(){tab("upload");});
  E.removeAudioBtn.addEventListener("click",clearFile);
  E.audioInput.addEventListener("change",function(){setFile(E.audioInput.files && E.audioInput.files[0]);});
  E.dropZone.addEventListener("click",function(){E.audioInput.click();});
  E.dropZone.addEventListener("keydown",function(ev){
    if(ev.key === "Enter" || ev.key === " "){ev.preventDefault();E.audioInput.click();}
  });
  ["dragenter","dragover"].forEach(function(evName){
    E.dropZone.addEventListener(evName,function(ev){ev.preventDefault();E.dropZone.classList.add("over");});
  });
  ["dragleave","drop"].forEach(function(evName){
    E.dropZone.addEventListener(evName,function(ev){ev.preventDefault();E.dropZone.classList.remove("over");});
  });
  E.dropZone.addEventListener("drop",function(ev){setFile(ev.dataTransfer && ev.dataTransfer.files && ev.dataTransfer.files[0]);});
  function mimeForRecorder() {
    var types=["audio/webm;codecs=opus","audio/webm","audio/ogg;codecs=opus"];
    return types.find(function(t){return MediaRecorder.isTypeSupported(t);});
  }
  async function cleanup() {
    if(S.timer){clearInterval(S.timer);S.timer=null;}
    if(S.stream){S.stream.getTracks().forEach(function(t){t.stop();});S.stream=null;}
    if(S.microphoneNode){try{S.microphoneNode.disconnect();}catch(_){} S.microphoneNode=null;}
    if(S.audioCtx){try{await S.audioCtx.close();}catch(_){} S.audioCtx=null;}
    S.analyser=null;
  }
  async function beginRecording() {
    if(S.recording || S.busy) return;
    if(!window.isSecureContext || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia ||
       typeof MediaRecorder === "undefined") return notify("This browser needs HTTPS and microphone recording support.",true);
    var type=mimeForRecorder();
    if(!type) return notify("This browser cannot record supported WebM/Opus or OGG/Opus audio.",true);
    S.busy=true;clearFile();updateButtons();
    try {
      S.stream = await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true}});
      S.chunks=[];
      var recorder=new MediaRecorder(S.stream,{mimeType:type});
      S.recorder=recorder;
      recorder.ondataavailable=function(ev){if(ev.data && ev.data.size) S.chunks.push(ev.data);};
      recorder.onerror=function(ev){notify("Recorder failed: "+((ev.error&&ev.error.message)||"unknown error"),true);};
      recorder.onstop=async function(){
        var blob=new Blob(S.chunks,{type:recorder.mimeType || type});
        await cleanup();
        S.recording=false;S.busy=false;S.recorder=null;
        E.recordPane.classList.remove("recording");
        E.recordBtn.textContent="●  Record again";
        E.recordHint.textContent=blob.size?"Recording ready to transcribe.":"No sound was captured.";
        if(blob.size) setFile(new File([blob],"sonicagent-recording."+(type.indexOf("ogg")>=0?"ogg":"webm"),{type:blob.type}));
        updateButtons();
      };
      recorder.start(250);
      S.start=Date.now();S.recording=true;S.busy=false;
      E.recordPane.classList.add("recording");
      E.recordBtn.textContent="■  Stop recording";
      E.recordHint.textContent="Recording locally. Audio is sent only when you click Transcribe.";
      S.timer=setInterval(function(){
        var sec=Math.floor((Date.now()-S.start)/1000);
        E.recordTime.textContent=String(Math.floor(sec/60)).padStart(2,"0")+":"+String(sec%60).padStart(2,"0");
        if(sec >= (S.mode === "demo"?S.demoSeconds:S.limitSeconds)) endRecording();
      },220);
      try{
        S.audioCtx=new (window.AudioContext||window.webkitAudioContext)();
        S.microphoneNode=S.audioCtx.createMediaStreamSource(S.stream);
        S.analyser=S.audioCtx.createAnalyser();
        S.analyser.fftSize=1024;S.microphoneNode.connect(S.analyser);
      }catch(_){S.analyser=null;}
      updateButtons();
    } catch(err) {
      S.recording=false;S.busy=false;await cleanup();updateButtons();
      notify("Microphone unavailable: "+err.message,true);
    }
  }
  function endRecording() {
    if(!S.recorder || S.recorder.state === "inactive") return;
    S.busy=true;E.recordHint.textContent="Preparing recording…";
    S.recorder.stop();updateButtons();
  }
  E.recordBtn.addEventListener("click",function(){S.recording?endRecording():beginRecording();});

  var canvas=E.waveCanvas, ctx=canvas.getContext("2d"), frame=0;
  function visualize() {
    if(ctx) {
      var width=canvas.clientWidth || 450, height=canvas.clientHeight || 54;
      var dpr=Math.min(window.devicePixelRatio || 1,2);
      if(canvas.width!==Math.round(width*dpr)||canvas.height!==Math.round(height*dpr)){
        canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);
      }
      ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,width,height);
      var frequency=null;
      if(S.recording && S.analyser) {
        frequency=new Uint8Array(S.analyser.frequencyBinCount);
        S.analyser.getByteFrequencyData(frequency);
      }
      var bins=58;
      for(var i=0;i<bins;i++){
        var raw=frequency?frequency[Math.floor(i*frequency.length/bins)]/255:0.05+0.05*(Math.sin(frame*.03+i*.5)+1);
        var envelope=Math.pow(Math.max(0,1-Math.abs(i-bins/2)/(bins/2)),.7);
        var amplitude=4+raw*height*.82*envelope;
        ctx.fillStyle=frequency?"#b89aff":"#5e5277";
        var bw=width/bins;
        ctx.fillRect(i*bw+bw*.22,(height-amplitude)/2,Math.max(2,bw*.55),amplitude);
      }
    }
    frame++;
    S.raf=requestAnimationFrame(visualize);
  }
  visualize();

  E.transcribeBtn.addEventListener("click",async function(){
    if(S.busy || !S.file) return;
    if(!authenticated()) return notify("Enable a demo or enter an API token first.",true);
    S.busy=true;updateButtons();E.transcribeBtn.querySelector("span").textContent="Transcribing…";
    E.transcriptText.textContent="Processing audio with Whisper. CPU inference may take some time…";
    E.resultMeta.hidden=true;E.copyBtn.disabled=true;
    var form=new FormData();
    form.append("file",S.file,S.file.name || "recording.webm");
    form.append("language",E.languageSelect.value);
    if(S.mode !== "demo")form.append("request_id","ui_"+Date.now()+"_"+Math.random().toString(36).slice(2,8));
    var endpoint=S.mode==="demo"?"/demo/transcriptions":"/v1/audio/transcriptions";
    try{
      var start=performance.now();
      var resp=await request(endpoint,{method:"POST",headers:headers(),body:form},90000);
      if(!resp.ok)throw new Error(await errorMessage(resp));
      var result=await resp.json();
      S.transcript=String(result.text || "").trim();
      E.transcriptText.textContent=S.transcript || "No speech detected. Try recording again.";
      E.transcriptText.classList.toggle("has-text",!!S.transcript);
      E.copyBtn.disabled=!S.transcript;
      E.resultMeta.hidden=false;
      E.resultMeta.textContent=(result.language || "auto").toUpperCase()+" · "+(result.model || "Whisper")+" · "+((performance.now()-start)/1000).toFixed(1)+"s";
      notify(S.transcript?"Transcription complete":"No speech detected");
    } catch(err) {
      E.transcriptText.textContent="Transcription failed: "+(err.name==="AbortError"?"request timed out":err.message);
      E.transcriptText.classList.remove("has-text");
      notify("Speech recognition unavailable: "+err.message,true);
    } finally {
      S.busy=false;E.transcribeBtn.querySelector("span").textContent="Transcribe audio";updateButtons();
    }
  });
  E.copyBtn.addEventListener("click",async function(){
    if(!S.transcript)return;
    try{await navigator.clipboard.writeText(S.transcript);notify("Copied transcript");}
    catch(_){notify("Clipboard access unavailable",true);}
  });

  var voices={
    "en-US":[["en_US-kristin-medium","Kristin · Companion","companion"],["en_US-lessac-medium","Lessac · Secretary","secretary"]],
    "en-GB":[["en_GB-cori-medium","Cori · Companion","companion"],["en_GB-alba-medium","Alba · Secretary","secretary"]],
    "es-ES":[["es_ES-sharvard-companion","Sharvard · Companion","companion"],["es_ES-sharvard-secretary","Sharvard · Secretary","secretary"]],
    "es-MX":[["es_MX-ald-companion","Ald · Companion","companion"],["es_MX-ald-medium","Ald · Secretary","secretary"]],
    "fr-FR":[["fr_FR-upmc-medium","Jessica · Companion","companion"],["fr_FR-siwis-medium","Siwis · Secretary","secretary"]],
    "de-DE":[["de_DE-eva_k-x_low","Eva K · Companion","companion"],["de_DE-kerstin-low","Kerstin · Secretary","secretary"]],
    "it-IT":[["it_IT-paola-companion","Paola · Companion","companion"],["it_IT-paola-medium","Paola · Secretary","secretary"]]
  };
  function selectedVoice() {
    var list=voices[E.ttsLanguage.value] || voices["en-US"];
    for (var i=0;i<list.length;i++) if (list[i][0]===E.ttsVoice.value) return list[i];
    return list[0];
  }
  function voiceNotice() {
    var item=selectedVoice();
    if (item[2]==="companion") return "Companion voice: warmer, slower, and softer. The WAV stays in this browser tab.";
    return "Secretary voice: clearer and a little faster, for work. The WAV stays in this browser tab.";
  }
  function renderVoices() {
    var previous=E.ttsVoice.value;
    E.ttsVoice.replaceChildren();
    (voices[E.ttsLanguage.value] || voices["en-US"]).forEach(function(item){
      var option=document.createElement("option");option.value=item[0];option.textContent=item[1];E.ttsVoice.append(option);
    });
    if (previous) E.ttsVoice.value=previous;
    if (!E.ttsVoice.value) E.ttsVoice.selectedIndex=0;
    updateButtons();
  }
  renderVoices();
  E.ttsLanguage.addEventListener("change",renderVoices);
  E.ttsInput.addEventListener("input",function(){
    E.charCounter.textContent=E.ttsInput.value.length+" / "+E.ttsInput.maxLength;updateButtons();
  });
  E.synthesizeBtn.addEventListener("click",async function(){
    if(S.busy || !authenticated() || !E.ttsInput.value.trim())return;
    S.busy=true;updateButtons();E.synthesizeBtn.querySelector("span").textContent="Synthesizing…";
    E.audioResultTitle.textContent="Generating voice…";
    E.audioResultSubtitle.textContent="Piper synthesis in progress";
    var body={
      text:E.ttsInput.value.trim(),voice:E.ttsVoice.value,
      language:E.ttsLanguage.value,format:"wav"
    };
    try {
      var resp=await request(S.mode==="demo"?"/demo/speech":"/v1/audio/speech",{
        method:"POST",headers:Object.assign({"Content-Type":"application/json"},headers()),
        body:JSON.stringify(body)
      },90000);
      if(!resp.ok)throw new Error(await errorMessage(resp));
      if(!/audio|octet-stream/i.test(resp.headers.get("content-type") || ""))throw new Error("Expected WAV audio");
      var blob=await resp.blob();
      if(!blob.size)throw new Error("Empty speech response");
      if(S.audioUrl)URL.revokeObjectURL(S.audioUrl);
      S.audioUrl=URL.createObjectURL(blob);
      E.audioPlayer.src=S.audioUrl;E.audioPlayer.hidden=false;
      E.audioResultTitle.textContent="Voice generated";
      E.audioResultSubtitle.textContent=fmtBytes(blob.size)+" · WAV · press play below";
      notify("Piper voice generated");
    } catch(err){
      E.audioResultTitle.textContent="Voice unavailable";
      E.audioResultSubtitle.textContent=err.name==="AbortError"?"Request timed out":err.message;
      notify("Piper error: "+err.message,true);
    } finally{
      S.busy=false;E.synthesizeBtn.querySelector("span").textContent="Generate voice";updateButtons();
    }
  });
  window.addEventListener("pagehide",function(){
    if(S.stream)S.stream.getTracks().forEach(function(t){t.stop();});
    if(S.audioUrl)URL.revokeObjectURL(S.audioUrl);
    cancelAnimationFrame(S.raf);clearInterval(S.timer);
    S.token="";E.tokenInput.value="";
  });
  Promise.allSettled([status(),getDemo()]);
  updateButtons();
})();
