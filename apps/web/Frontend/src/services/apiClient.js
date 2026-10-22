import axios from "axios";

const apiClient = axios.create({
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
  baseURL: import.meta.env.VITE_API_BASE_URL,
});

export default apiClient;
