"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { motion } from "framer-motion";
import { Users, Search, Check, X, UserMinus, ChevronRight, UserPlus } from "lucide-react";
import { Link } from "@/i18n/navigation";
import { friendsApi } from "@/lib/api";
import { Navbar } from "@/components/ui/Navbar";
import { cn } from "@/lib/utils";

interface UserSummary {
  id: number;
  name: string;
  avatar_url: string | null;
}

interface SearchResult extends UserSummary {
  friendship_status: string;
}

interface FriendRequest {
  friendship_id: number;
  user: UserSummary;
  created_at: string;
}

interface Friend {
  friendship_id: number;
  user: UserSummary;
}

function Avatar({ user, size = "md" }: { user: UserSummary; size?: "sm" | "md" }) {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL?.replace("/api/v1", "") ?? "http://localhost:8000";
  const cls = size === "sm" ? "w-7 h-7 text-xs" : "w-9 h-9 text-sm";
  if (user.avatar_url) {
    return <img src={`${apiBaseUrl}${user.avatar_url}`} alt={user.name} className={cn(cls, "rounded-full object-cover border border-slate-600")} />;
  }
  return (
    <div className={cn(cls, "rounded-full bg-brand-500/20 border border-brand-500/30 flex items-center justify-center shrink-0")}>
      <span className="font-bold text-brand-400">{user.name.charAt(0).toUpperCase()}</span>
    </div>
  );
}

export default function FriendsPage() {
  const t = useTranslations("friends");
  const qc = useQueryClient();
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [searchError, setSearchError] = useState("");

  const { data: requestsData } = useQuery({
    queryKey: ["friend-requests"],
    queryFn: () => friendsApi.listRequests().then((r) => r.data),
  });
  const { data: friendsData } = useQuery({
    queryKey: ["friends"],
    queryFn: () => friendsApi.list().then((r) => r.data),
  });

  const searchMutation = useMutation({
    mutationFn: () => friendsApi.search(query),
    onSuccess: (res) => {
      setSearchResults(res.data.users);
      setSearchError("");
    },
    onError: () => setSearchError(t("errorSearch")),
  });

  const sendRequestMutation = useMutation({
    mutationFn: (id: number) => friendsApi.sendRequest(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["friend-requests"] });
      if (query) searchMutation.mutate();
    },
  });

  const acceptMutation = useMutation({
    mutationFn: (friendshipId: number) => friendsApi.acceptRequest(friendshipId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["friend-requests"] });
      qc.invalidateQueries({ queryKey: ["friends"] });
    },
  });

  const declineMutation = useMutation({
    mutationFn: (friendshipId: number) => friendsApi.declineRequest(friendshipId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["friend-requests"] }),
  });

  const removeMutation = useMutation({
    mutationFn: (friendId: number) => friendsApi.remove(friendId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["friends"] }),
  });

  const requests: FriendRequest[] = requestsData?.requests ?? [];
  const friends: Friend[] = friendsData?.friends ?? [];

  return (
    <div className="min-h-screen lg:pl-60">
      <Navbar />
      <main className="px-4 py-6 pb-24 lg:pb-6 max-w-2xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="space-y-8">

          {/* Header */}
          <div>
            <h1 className="text-xl font-bold text-white">{t("title")}</h1>
            <p className="text-sm text-slate-400 mt-1">{t("subtitle")}</p>
          </div>

          {/* Search */}
          <section className="space-y-3">
            <label className="text-sm font-semibold text-slate-300">{t("searchLabel")}</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && query.trim().length >= 2 && searchMutation.mutate()}
                placeholder={t("searchPlaceholder")}
                className="flex-1 bg-surface-elevated border border-slate-700 rounded-xl px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
              />
              <button
                onClick={() => searchMutation.mutate()}
                disabled={query.trim().length < 2 || searchMutation.isPending}
                className="px-4 py-2 rounded-xl bg-brand-500 text-white text-sm font-medium hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                <Search className="w-4 h-4" />
                {t("searchButton")}
              </button>
            </div>

            {searchError && <p className="text-sm text-red-400">{searchError}</p>}

            {searchResults !== null && (
              <div className="space-y-2">
                {searchResults.length === 0 ? (
                  <p className="text-sm text-slate-500 text-center py-4">{t("noResults")}</p>
                ) : (
                  searchResults.map((u) => (
                    <div key={u.id} className="card flex items-center gap-3">
                      <Avatar user={u} />
                      <span className="flex-1 text-sm font-medium text-white">{u.name}</span>
                      {u.friendship_status === "none" && (
                        <button
                          onClick={() => sendRequestMutation.mutate(u.id)}
                          disabled={sendRequestMutation.isPending}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-500/15 text-brand-300 text-xs font-medium hover:bg-brand-500/25 transition-colors"
                        >
                          <UserPlus className="w-3.5 h-3.5" />
                          {t("sendRequest")}
                        </button>
                      )}
                      {u.friendship_status === "pending" && (
                        <span className="text-xs text-slate-500 px-2 py-1 rounded-lg bg-slate-700/50">{t("requestPending")}</span>
                      )}
                      {u.friendship_status.startsWith("incoming_") && (
                        <span className="text-xs text-amber-400">{t("incoming")}</span>
                      )}
                      {u.friendship_status === "accepted" && (
                        <span className="text-xs text-emerald-400">{t("alreadyFriends")}</span>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </section>

          {/* Pending requests */}
          <section className="space-y-3">
            <h2 className="text-sm font-semibold text-slate-300">{t("pendingRequests")}</h2>
            {requests.length === 0 ? (
              <p className="text-sm text-slate-500">{t("noPendingRequests")}</p>
            ) : (
              <div className="space-y-2">
                {requests.map((req) => (
                  <div key={req.friendship_id} className="card flex items-center gap-3">
                    <Avatar user={req.user} />
                    <span className="flex-1 text-sm font-medium text-white">{req.user.name}</span>
                    <button
                      onClick={() => acceptMutation.mutate(req.friendship_id)}
                      className="p-1.5 rounded-lg bg-emerald-500/15 text-emerald-400 hover:bg-emerald-500/25 transition-colors"
                      title={t("accept")}
                    >
                      <Check className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => declineMutation.mutate(req.friendship_id)}
                      className="p-1.5 rounded-lg bg-red-500/15 text-red-400 hover:bg-red-500/25 transition-colors"
                      title={t("decline")}
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Friends list */}
          <section className="space-y-3">
            <h2 className="text-sm font-semibold text-slate-300">{t("friendsList")}</h2>
            {friends.length === 0 ? (
              <div className="card text-center py-10 space-y-2">
                <Users className="w-9 h-9 text-slate-600 mx-auto" />
                <p className="text-sm text-slate-500">{t("noFriends")}</p>
              </div>
            ) : (
              <div className="space-y-2">
                {friends.map((f) => (
                  <div key={f.friendship_id} className="card flex items-center gap-3 group">
                    <Avatar user={f.user} />
                    <span className="flex-1 text-sm font-medium text-white">{f.user.name}</span>
                    <Link
                      href={`/friends/${f.user.id}`}
                      className="flex items-center gap-1 text-xs text-brand-400 hover:text-brand-300 transition-colors"
                    >
                      {t("activities")}
                      <ChevronRight className="w-3.5 h-3.5" />
                    </Link>
                    <button
                      onClick={() => {
                        if (confirm(t("removeConfirm"))) removeMutation.mutate(f.user.id);
                      }}
                      className="p-1.5 rounded-lg text-slate-600 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                      title={t("remove")}
                    >
                      <UserMinus className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>

        </motion.div>
      </main>
    </div>
  );
}
