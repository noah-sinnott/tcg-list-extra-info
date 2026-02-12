import axios from 'axios';

// const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000/api';
const API_URL = 'https://backend-tcg-912009530954.europe-west2.run.app/api';

export async function scrapeLists(sources) {
  const response = await axios.post(`${API_URL}/scrape`, { sources });
  return response.data.cards;
}
