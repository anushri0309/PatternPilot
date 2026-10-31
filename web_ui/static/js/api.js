(function () {
  'use strict';

  const CONFIG = {
    USE_MOCK: false,
    BASE_URL: 'http://127.0.0.1:5000/api',
    FEATURES: { methodSelector: false },
    FORCE_ERROR: false,
  };

  const OPTIONS = {
    garment_type: [['t-shirt', 'T-shirt'], ['blouse', 'Blouse / top'], ['shirt', 'Shirt'], ['jeans', 'Jeans'], ['pants', 'Pants'], ['skirt', 'Skirt'], ['dress', 'Dress']],
    silhouette: [['fitted', 'Fitted'], ['loose', 'Loose'], ['oversized', 'Oversized'], ['a-line', 'A-line'], ['circle', 'Circle / flared'], ['bootcut', 'Bootcut']],
    neckline: [['round', 'Round'], ['v', 'V-neck'], ['halter', 'Halter'], ['square', 'Square'], ['off-shoulder', 'Off-shoulder'], ['collared', 'Collared']],
    sleeve_length: [['sleeveless', 'Sleeveless'], ['short', 'Short'], ['elbow', 'Elbow'], ['three-quarter', '3/4 length'], ['long', 'Long']],
    waistline: [['natural_waist', 'Natural'], ['high_waist', 'High / Empire'], ['low_waist', 'Dropped'], ['no_waistline', 'No defined waist']],
    length: [['mini', 'Mini / Cropped'], ['hip', 'Hip length'], ['knee', 'Knee length'], ['midi', 'Midi'], ['maxi', 'Maxi'], ['floor', 'Floor length']],
  };

  const METHODS = [['aldrich', 'Aldrich (custom)']];
  const MEASURE_KEYS = ['bust', 'waist', 'hips', 'shoulder', 'length', 'sleeve'];

  async function http(path, opts) {
    const res = await fetch(CONFIG.BASE_URL + path, { credentials: 'include', ...opts });
    const data = await res.json().catch(() => null);
    if (!res.ok) throw new Error((data && data.message) || `Error (${res.status}).`);
    return data;
  }
  const jsonPost = (path, body) => http(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

  const real = {
    login: (email, password) => jsonPost('/auth/login', { email, password }),
    logout: () => jsonPost('/auth/logout', {}),

    async analyzeGarment(file) {
      const fd = new FormData(); fd.append('image', file);
      const data = await http('/analyze', { method: 'POST', body: fd });
      return data;
    },

    async generatePattern(payload) {
      const data = await jsonPost('/generate', payload);
      return { svg: data.svg };
    }
  };

  window.PatternPilotAPI = {
    ...real,
    CONFIG, OPTIONS, METHODS, MEASURE_KEYS
  };
})();