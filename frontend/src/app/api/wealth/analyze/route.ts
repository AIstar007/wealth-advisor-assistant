import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function POST(request: Request) {
  const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: "Request body must be valid JSON." }, { status: 400 });
  }

  try {
    const response = await fetch(`${backendUrl}/v1/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const text = await response.text();
    return new NextResponse(text, {
      status: response.status,
      headers: { "Content-Type": response.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return NextResponse.json(
      { detail: "Could not reach the Wealth Advisor backend. Check that FastAPI is running." },
      { status: 502 },
    );
  }
}
