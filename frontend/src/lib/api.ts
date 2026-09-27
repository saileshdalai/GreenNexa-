// GreenNexa API Client

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001";

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
      } catch {}
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
