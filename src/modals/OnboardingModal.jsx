import React, { useState, useEffect } from 'react';
import { ArrowRight, LoaderCircle } from 'lucide-react';
import Field from '@/components/content-components/right-panel-components/Field';
import Tooltip from '@/components/Tooltip';

import note from '@/assets/note-element.svg'

function OnboardingModal({onComplete}) {
  const [userName, setUserName] = useState('');
  const [page, setPage] = useState(0);

  const handleUpdateUser = () => {
    window.electronAPI.updateUserSettings('needs_onboarding', false);
    onComplete();
  };
  
  const handleUserNameChange = (name) => {
    setUserName(name);
    window.electronAPI.updateUserSettings('user_name', name);
  }

  useEffect(() => {
    if (page === 1) {
      const timeout = setTimeout(() => {
        handleUpdateUser();
      }, 4000 + Math.random() * 500);

      return () => clearTimeout(timeout);
    }
  }, [page]);

  return (
    <>
      <img src={note} style={{opacity: '0.9', position: 'absolute', left: '540px', top: '90px'}}></img>
      <div className='modal-big-title' text-style='display' style={{margin : '15px 0px', width: '500px'}}>Welcome to Symphony v1.0</div>
      {page === 0 ? (<>
        <div className='modal-big-body' text-style='display'>What's your name?</div>
        <div style={{display: 'flex', flexDirection: 'row', gap: '10px'}}>
          <Field
            defaultText={'Enter Name Here'}
            value={userName}
            className='field onboarding-field'
            lightDark={['#d9d9d977','#d9d9d9']}
            height='38px'
            fontSize='16px'
            onChange={e => handleUserNameChange(e.target.value || '')}
            singleLine={true}
            isControlled={true}
            width={'300px'}
          />
          <button className={'onboarding-button tooltip'} text-style='display' onClick={() => setPage(1)}><Tooltip text={userName? 'Continue' : 'Skip'}/><ArrowRight /></button>
        </div>
      </>) : (<>
        <div text-style='display' style={{height: '120px', fontSize: '20px', display: 'flex', alignItems:'center', gap: '10px'}}><LoaderCircle className="spin"/>Getting things ready for you...</div>
      </>)}
      <div style={{width: '470px', marginTop: '80px'}}>We do not share your information with any third parties. Your name is only used to address you personally inside the application, and is competely voluntary.</div>
    </>
  );
}

export default OnboardingModal;