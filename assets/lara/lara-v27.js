(() => {
  'use strict';
  const root=document.getElementById('lara-root');
  if(!root||root.dataset.v27Enhancements==='true')return;
  root.dataset.v27Enhancements='true';
  const profiles={
    global:{label:'Global LaRA',locale:'en',voiceHint:'global'},
    chinese:{label:'Chinese-language LaRA',locale:'zh-CN',voiceHint:'zh'},
    japanese:{label:'Japanese-language LaRA',locale:'ja-JP',voiceHint:'ja'},
  };
  const panel=root.querySelector('.lara-panel'),state=root.querySelector('.lara-avatar-state'),input=root.querySelector('.lara-input');
  const setState=(value,label)=>{root.dataset.avatarState=value;if(state)state.textContent=label||value;const avatar=root.querySelector('.lara-avatar-2d');if(avatar)avatar.setAttribute('aria-label','LaRA is '+(label||value));};
  const stored=(()=>{try{return sessionStorage.getItem('lara.avatar.profile');}catch{return null;}})();
  const profile=document.createElement('label');profile.className='lara-avatar-profile';profile.innerHTML='<span>Avatar profile</span><select aria-label="LaRA avatar profile"></select>';
  const profileSelect=profile.querySelector('select');
  for(const [id,definition] of Object.entries(profiles)){const option=document.createElement('option');option.value=id;option.textContent=definition.label;profileSelect.append(option);}
  profileSelect.value=profiles[stored]?stored:'global';
  const applyProfile=()=>{const selected=profileSelect.value;root.dataset.avatarProfile=selected;try{sessionStorage.setItem('lara.avatar.profile',selected);}catch{};};
  applyProfile();profileSelect.addEventListener('change',applyProfile);
  root.querySelector('.lara-style-label')?.insertAdjacentElement('afterend',profile);

  let recognition=null,recognitionActive=false,utterance=null;
  const controls=document.createElement('div');controls.className='lara-v27-voice-controls';
  controls.innerHTML='<label>Voice rate <select aria-label="Voice playback rate"><option value="0.9">Slow</option><option value="1" selected>Normal</option><option value="1.1">Fast</option></select></label><button type="button" class="lara-voice-pause" disabled>Pause</button><button type="button" class="lara-voice-stop" disabled>Stop</button><button type="button" class="lara-listen-stop" disabled>Stop listening</button>';
  root.querySelector('.lara-footer')?.insertAdjacentElement('beforebegin',controls);
  const rate=controls.querySelector('select'),pause=controls.querySelector('.lara-voice-pause'),stop=controls.querySelector('.lara-voice-stop'),stopListening=controls.querySelector('.lara-listen-stop');
  const textForSpeech=button=>button.closest('.lara-message')?.querySelector('.lara-prose')?.textContent?.trim()||'';
  const speak=(text,language)=>{if(!('speechSynthesis' in window)||!text)return;window.speechSynthesis.cancel();utterance=new SpeechSynthesisUtterance(text);utterance.lang={zh:'zh-CN',ja:'ja-JP',ko:'ko-KR',sk:'sk-SK'}[language]||language||profiles[profileSelect.value].locale||'en';utterance.rate=Number(rate.value);utterance.onstart=()=>{setState('speaking','Speaking');pause.disabled=false;stop.disabled=false;};utterance.onend=utterance.onerror=()=>{utterance=null;pause.disabled=true;stop.disabled=true;if(!recognitionActive)setState('success','Complete');};window.speechSynthesis.speak(utterance);};
  root.addEventListener('click',event=>{const button=event.target.closest('.lara-message-tools button:nth-child(2)');if(!button)return;event.preventDefault();event.stopImmediatePropagation();const message=button.closest('.lara-message');speak(textForSpeech(button),message?.querySelector('.lara-mode-tag')?.textContent?.match(/\b(zh|ja|ko|sk|en|de|fr|it|es|pt)\b/i)?.[1]);},true);
  pause.addEventListener('click',()=>{if(!utterance)return;if(window.speechSynthesis.paused){window.speechSynthesis.resume();pause.textContent='Pause';setState('speaking','Speaking');}else{window.speechSynthesis.pause();pause.textContent='Resume';setState('idle','Paused');}});
  stop.addEventListener('click',()=>{window.speechSynthesis?.cancel();utterance=null;pause.disabled=true;stop.disabled=true;setState('idle','Ready');});
  root.querySelector('.lara-listen')?.addEventListener('click',event=>{event.preventDefault();event.stopImmediatePropagation();const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;if(!Recognition){root.querySelector('.lara-status').textContent='Voice input is not available in this browser.';return;}if(recognitionActive)return;recognition=new Recognition();const language=root.querySelector('.lara-language')?.value||'auto';recognition.lang={auto:navigator.language||'en',zh:'zh-CN',ja:'ja-JP',ko:'ko-KR',sk:'sk-SK'}[language]||language;recognition.interimResults=true;recognition.onstart=()=>{recognitionActive=true;stopListening.disabled=false;setState('listening','Listening');};recognition.onresult=event=>{input.value=[...event.results].map(result=>result[0].transcript).join(' ');};recognition.onerror=event=>{root.querySelector('.lara-status').textContent=event.error==='not-allowed'?'Microphone permission was denied.':'Voice input could not be started.';setState('error','Voice input error');};recognition.onend=()=>{recognitionActive=false;stopListening.disabled=true;if(root.dataset.avatarState==='listening')setState('idle','Ready');};try{recognition.start();}catch{root.querySelector('.lara-status').textContent='Voice input is already starting.';}} ,true);
  stopListening.addEventListener('click',()=>{if(recognition)recognition.stop();});
  const browserPerformance=window.performance;
  const traces={events:[],start(kind){const item={id:window.crypto?.randomUUID?.()||String(Date.now()),kind,started_at:browserPerformance.now()};traces.events.push(item);return item;},finish(item,detail={}){item.total_ms=Math.round(browserPerformance.now()-item.started_at);item.detail=detail;return {...item};}};
  root.querySelector('.lara-form')?.addEventListener('submit',()=>{const trace=traces.start('chat');const done=()=>{traces.finish(trace,{responsive:Boolean(panel?.classList.contains('is-open'))});root.removeEventListener('lara-v27-response',done);};root.addEventListener('lara-v27-response',done,{once:true});},{capture:true});
  const observer=new MutationObserver(()=>{if(!root.querySelector('.lara-pending'))root.dispatchEvent(new Event('lara-v27-response'));});observer.observe(root.querySelector('.lara-messages'),{childList:true,subtree:true});
  window.LaRAV27={profiles,performance:()=>traces.events.map(item=>({...item})),stopVoice:()=>stop.click(),stopListening:()=>stopListening.click()};
})();
