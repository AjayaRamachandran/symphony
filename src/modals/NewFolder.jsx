import React from 'react';

import Field from '@/components/content-components/right-panel-components/Field'


function NewFolder() {
  return (
    <>
      <div className='modal-title' text-style='display'>Add New Folder</div>
      <div className='modal-body'>Original File Location</div>
      <Field defaultText='' height="31px" fontSize='0.8em' width='320px' whiteSpace='nowrap' />

      <div className='modal-body' style={{marginTop: '2em'}}>Destination</div>
      <Field defaultText='' height="31px" fontSize='0.8em' width='320px' whiteSpace='nowrap' />
    </>
  );
}

export default NewFolder;