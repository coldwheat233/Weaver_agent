export const API = "http://localhost:8765";

export interface IdeaNode {
  id: string;
  source_type: string;
  standardized_content: string;
  raw_content: string;
  intent_tags: string[];
  context_tags: string[];
  status: string;
  created_at: string;
}

export interface DesignDoc {
  design_id: string;
  title: string;
  type: string;
  innovation_score: number;
  coherence_score: number;
  feasibility_score: number;
  critic_approval: boolean;
  version: number;
}

export interface Session {
  session_id: string;
  north_star: string;
  status: string;
  output_design_id: string | null;
}

export interface V3Proposal {
  cluster_name: string;
  node_count: number;
  cross_domains: number;
  status: string;
  design_id?: string;
}

export interface InquisitorQuestion {
  priority: number;
  question: string;
  context: string;
  category: string;
}

// API helpers
async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

async function post<T>(path: string, body?: any): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    method: "POST",
    headers: body instanceof FormData ? {} : { "Content-Type": "application/json" },
    body: body instanceof FormData ? body : JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

export const api = {
  submitIdea: (content: string, sessionId?: string) => {
    const fd = new FormData();
    fd.append("content", content);
    if (sessionId) fd.append("session_id", sessionId);
    return post<{ idea_id: string }>("/api/ideas", fd);
  },
  createSession: (northStar: string) =>
    post<Session>("/api/sessions", { north_star: northStar }),
  getSession: (sid: string) => get<Session>(`/api/sessions/${sid}`),
  triggerWeave: (sid: string) =>
    post<{ status: string; design_id?: string }>(`/api/sessions/${sid}/weave`),
  getDesign: (did: string) => get<DesignDoc>(`/api/designs/${did}`),
  listDesigns: () => get<DesignDoc[]>("/api/designs"),
  listIdeas: () => get<IdeaNode[]>("/api/ideas"),
  checkInquisitor: (sid: string) =>
    post<{ questions: InquisitorQuestion[] }>(`/api/v2/ask?session_id=${sid}`),
  listProposals: () =>
    get<{ proposals: V3Proposal[]; pending: number }>("/api/v3/proposals"),
};
