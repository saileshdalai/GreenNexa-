"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import Header from "./Header";
import { Sidebar } from "./Sidebar";
import { ToastContainer } from "@/components/ui/ToastContainer";
import { Skeleton } from "@/components/ui/Skeleton";
import { DemoBanner } from "@/components/demo/DemoBanner";
import { DemoWalkthroughModal } from "@/components/demo/DemoWalkthroughModal";
import GreenNexaAssistant from "@/components/ai/GreenNexaAssistant";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    if (typeof window !== "undefined") {
      return window.innerWidth < 1024;
    }
    return false;
  });

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768) {
        setCollapsed(true);
      }
    };
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [loading, user, router]);

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "var(--clr-bg)" }}>
        <Header />
        <div style={{ padding: "40px", flex: 1, maxWidth: "1200px", margin: "0 auto", width: "100%" }}>
          <Skeleton height="40px" width="300px" style={{ marginBottom: "24px" }} />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "20px" }}>
            <Skeleton height="120px" />
            <Skeleton height="120px" />
            <Skeleton height="120px" />
          </div>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "var(--clr-bg)" }}>
      <Header />
      <DemoBanner />
      <DemoWalkthroughModal />
      <ToastContainer />
      <div style={{ display: "flex", flex: 1, position: "relative", minWidth: 0, width: "100%" }}>
        <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
        <main
          className="app-main-content"
          style={{
            flex: 1,
            maxWidth: "1400px",
            width: "100%",
            minWidth: 0,
          }}
        >
          {children}
        </main>
      </div>
      <GreenNexaAssistant />
    </div>
  );
}
