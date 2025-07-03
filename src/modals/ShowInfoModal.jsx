import React, { useEffect, useState, useRef } from 'react';
import { Info } from 'lucide-react';

function ShowInfoModal({ filePath }) {
  const [fileInfo, setFileInfo] = useState(null);
  const [error, setError] = useState(null);
  const hasFetched = useRef(false);  // <-- Track if fetch has already run

  useEffect(() => {
    if (hasFetched.current || !filePath) return;

    hasFetched.current = true;  // prevent future runs

    const fetchInfo = async () => {
      try {
        const result = await window.electronAPI.runPythonRetrieve(filePath);

        if (result?.fileInfo) {
          setFileInfo(result.fileInfo);
        } else {
          setError(result?.error || 'Unknown error retrieving file info');
        }
      } catch (err) {
        setError(err.message || 'Failed to retrieve info');
      }
    };

    fetchInfo();
  }, [filePath]);

  return (
    <>
      <div className="modal-title" text-style="display" style={{ display: 'flex', marginBottom: '15px', alignItems: 'center' }}>
        File Properties
      </div>

      {error && (
        <div className="modal-paragraph text-red-500">
          Error: {error}
        </div>
      )}

      {!fileInfo && !error && (
        <div className="modal-paragraph text-gray-500">
          Loading file info...
        </div>
      )}

      {fileInfo && (
        <div className="modal-paragraph space-y-2" style={{marginBottom: '10px'}}>
          {Object.entries(fileInfo).map(([key, value]) => (
            <div key={key}>
              <strong style={{marginRight: '4px'}}>{key[0].toUpperCase() + key.slice(1)}:</strong>{' '}
              {typeof value === 'object' ? JSON.stringify(value) : String(value)}
            </div>
          ))}
        </div>
      )}
    </>
  );
}

export default ShowInfoModal;
