// GreenNexa API Client
// Priority: NEXT_PUBLIC_API_URL env var -> Production deployed fallback -> Localhost development fallback
function resolveApiBaseUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (envUrl) {
    // Normalize trailing slash and remove accidental trailing /api/v1 (endpoints prefix /api/v1)
    return envUrl.replace(/\/+$/, "").replace(/\/api\/v1$/, "");
  }

  // Production safeguard: Deployed frontend must never attempt loopback (localhost / 127.0.0.1)
  const isBrowser = typeof window !== "undefined";
  const isLocalHost =
    isBrowser &&
    (window.location.hostname === "localhost" ||
      window.location.hostname === "127.0.0.1" ||
      window.location.hostname === "[::1]");

  if (process.env.NODE_ENV === "production" || (isBrowser && !isLocalHost)) {
    return "https://greennexa-3k2u.onrender.com";
  }

  // Local development fallback
  return "http://127.0.0.1:8001";
}

export const API_BASE_URL = resolveApiBaseUrl();
const BASE_URL = API_BASE_URL;

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.status = status;
    this.data = data;
    this.name = "ApiError";
  }
}

function getAuthHeader(): Record<string, string> {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("greennexa_token");
    if (token) {
      return { Authorization: `Bearer ${token}` };
    }
  }
  return {};
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errData: any;
    try {
      errData = await res.json();
    } catch {
      errData = { detail: res.statusText };
    }

    const message =
      typeof errData?.detail === "string"
        ? errData.detail
        : Array.isArray(errData?.detail)
          ? errData.detail.map((e: any) => e.msg).join(", ")
          : `Request failed with status ${res.status}`;

    if (res.status === 401 && typeof window !== "undefined") {
      // Clear token on 401
      localStorage.removeItem("greennexa_token");
    }

    throw new ApiError(res.status, message, errData);
  }

  return res.json();
}

export const api = {
  async get<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
    let url = `${BASE_URL}${endpoint}`;
    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, val]) => {
        if (val !== undefined && val !== null && val !== "") {
          searchParams.append(key, String(val));
        }
      });
      const qs = searchParams.toString();
      if (qs) url += `?${qs}`;
    }

    const res = await fetch(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeader(),
      },
    });

    return handleResponse<T>(res);
  },

  async post<T>(endpoint: string, body?: any): Promise<T> {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeader(),
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    return handleResponse<T>(res);
  },

  async patch<T>(endpoint: string, body?: any): Promise<T> {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeader(),
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    return handleResponse<T>(res);
  },

  async put<T>(endpoint: string, body?: any): Promise<T> {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeader(),
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    return handleResponse<T>(res);
  },

  async delete<T>(endpoint: string): Promise<T> {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeader(),
      },
    });

    return handleResponse<T>(res);
  },

  async downloadReport(endpoint: string, params: Record<string, any>): Promise<{ blob: Blob; filename: string }> {
    let url = `${BASE_URL}${endpoint}`;
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== "") {
        searchParams.append(key, String(val));
      }
    });
    const qs = searchParams.toString();
    if (qs) url += `?${qs}`;

    const res = await fetch(url, {
      method: "GET",
      headers: {
        ...getAuthHeader(),
      },
    });

    if (!res.ok) {
      let errText = "Failed to download report";
      try {
        const errJson = await res.json();
        errText = errJson.detail || errText;
      } catch { }
      throw new ApiError(res.status, errText);
    }

    const disposition = res.headers.get("content-disposition");
    let filename = "GreenNexa_Report";
    if (disposition && disposition.includes("filename=")) {
      const match = disposition.match(/filename="?([^"]+)"?/);
      if (match && match[1]) {
        filename = match[1];
      }
    }

    const blob = await res.blob();
    return { blob, filename };
  },
};
