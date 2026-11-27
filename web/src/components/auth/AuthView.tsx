import { useRef, useState, type FormEvent } from "react";
import { AlertCircle, Eye, EyeOff, Loader2 } from "lucide-react";

import { BrandMark } from "@/components/BrandMark";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuth } from "@/hooks/useAuth";

type Mode = "login" | "register";

function FieldError({ id, message }: { id: string; message: string | null }) {
  if (!message) return null;
  return (
    <p id={id} className="flex items-center gap-1.5 text-xs text-destructive">
      <AlertCircle className="size-3.5 shrink-0" aria-hidden="true" />
      <span>{message}</span>
    </p>
  );
}

export function AuthView() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<Mode>("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [touched, setTouched] = useState<{
    username?: boolean;
    email?: boolean;
    password?: boolean;
  }>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const usernameRef = useRef<HTMLInputElement>(null);
  const emailRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);

  const validateUsername = (v: string) => {
    if (mode !== "register") return null;
    const t = v.trim();
    if (t.length < 2 || t.length > 50) return "用户名需为 2–50 个字符";
    return null;
  };

  const validateEmail = (v: string) => {
    const t = v.trim();
    if (!t || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(t)) {
      return "请输入有效的邮箱地址，例如 you@example.com";
    }
    return null;
  };

  const validatePassword = (v: string) => {
    if (!v) return "请输入密码";
    if (mode === "register" && v.length < 6) return "密码至少需要 6 位字符";
    return null;
  };

  const usernameError = touched.username ? validateUsername(username) : null;
  const emailError = touched.email ? validateEmail(email) : null;
  const passwordError = touched.password ? validatePassword(password) : null;

  const switchMode = (next: string) => {
    setMode(next as Mode);
    setTouched({});
    setSubmitError(null);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    const uErr = validateUsername(username);
    const eErr = validateEmail(email);
    const pErr = validatePassword(password);
    setTouched({ username: true, email: true, password: true });

    if (uErr) {
      usernameRef.current?.focus();
      return;
    }
    if (eErr) {
      emailRef.current?.focus();
      return;
    }
    if (pErr) {
      passwordRef.current?.focus();
      return;
    }

    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(email.trim(), password);
      } else {
        await register(username.trim(), email.trim(), password);
      }
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "认证失败，请重试");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-dvh flex-col items-center justify-center bg-background px-4 py-10">
      <div className="w-full max-w-[400px]">
        <div className="mb-7 flex flex-col items-center text-center">
          <div className="mb-3.5 flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
            <BrandMark className="size-5" />
          </div>
          <h1 className="text-xl font-semibold tracking-tight text-foreground">Mentorly</h1>
          <p className="mt-1 text-xs text-muted-foreground">
            智能学习工作台 · 对话、工具轨迹与产物交付
          </p>
        </div>

        <div className="composer-surface rounded-2xl border border-border bg-card p-6 sm:p-7">
          <Tabs value={mode} onValueChange={switchMode}>
            <TabsList className="mb-6 grid w-full grid-cols-2">
              <TabsTrigger value="login">登录</TabsTrigger>
              <TabsTrigger value="register">注册</TabsTrigger>
            </TabsList>

            <TabsContent value={mode} forceMount>
              <form
                onSubmit={handleSubmit}
                noValidate
                aria-label={mode === "login" ? "登录表单" : "注册表单"}
              >
                <div className="space-y-4">
                  {mode === "register" && (
                    <div className="space-y-1.5">
                      <Label htmlFor="auth-username">
                        用户名 <span aria-hidden="true">*</span>
                      </Label>
                      <p id="auth-username-hint" className="text-xs text-muted-foreground">
                        2–50 个字符，将显示在个人资料与工作区
                      </p>
                      <Input
                        ref={usernameRef}
                        id="auth-username"
                        name="username"
                        type="text"
                        required
                        minLength={2}
                        maxLength={50}
                        autoComplete="username"
                        autoCorrect="off"
                        autoCapitalize="none"
                        spellCheck={false}
                        enterKeyHint="next"
                        value={username}
                        aria-invalid={usernameError ? "true" : "false"}
                        aria-describedby={
                          usernameError
                            ? "auth-username-hint auth-username-err"
                            : "auth-username-hint"
                        }
                        onChange={(e) => {
                          setUsername(e.target.value);
                          if (submitError) setSubmitError(null);
                        }}
                        onBlur={() => setTouched((prev) => ({ ...prev, username: true }))}
                        placeholder="例如：林知行"
                        className="h-10"
                      />
                      <FieldError id="auth-username-err" message={usernameError} />
                    </div>
                  )}

                  <div className="space-y-1.5">
                    <Label htmlFor="auth-email">
                      邮箱 <span aria-hidden="true">*</span>
                    </Label>
                    <Input
                      ref={emailRef}
                      id="auth-email"
                      name="email"
                      type="email"
                      required
                      maxLength={100}
                      autoComplete={mode === "login" ? "username" : "email"}
                      autoCorrect="off"
                      autoCapitalize="none"
                      spellCheck={false}
                      enterKeyHint="next"
                      value={email}
                      aria-invalid={emailError ? "true" : "false"}
                      aria-describedby={emailError ? "auth-email-err" : undefined}
                      onChange={(e) => {
                        setEmail(e.target.value);
                        if (submitError) setSubmitError(null);
                      }}
                      onBlur={() => setTouched((prev) => ({ ...prev, email: true }))}
                      placeholder="you@example.com"
                      className="h-10"
                    />
                    <FieldError id="auth-email-err" message={emailError} />
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="auth-password">
                      密码 <span aria-hidden="true">*</span>
                    </Label>
                    {mode === "register" && (
                      <p id="auth-password-hint" className="text-xs text-muted-foreground">
                        至少 6 位字符，最多 80 位
                      </p>
                    )}
                    <div className="relative">
                      <Input
                        ref={passwordRef}
                        id="auth-password"
                        name="password"
                        type={showPassword ? "text" : "password"}
                        required
                        minLength={mode === "register" ? 6 : 1}
                        maxLength={80}
                        autoComplete={mode === "login" ? "current-password" : "new-password"}
                        enterKeyHint="done"
                        value={password}
                        aria-invalid={passwordError ? "true" : "false"}
                        aria-describedby={
                          [
                            mode === "register" ? "auth-password-hint" : "",
                            passwordError ? "auth-password-err" : "",
                          ]
                            .filter(Boolean)
                            .join(" ") || undefined
                        }
                        onChange={(e) => {
                          setPassword(e.target.value);
                          if (submitError) setSubmitError(null);
                        }}
                        onBlur={() => setTouched((prev) => ({ ...prev, password: true }))}
                        placeholder={mode === "login" ? "输入登录密码" : "设置登录密码"}
                        className="h-10 pr-10"
                      />
                      <button
                        type="button"
                        aria-pressed={showPassword}
                        aria-label={showPassword ? "隐藏密码" : "显示密码"}
                        onClick={() => setShowPassword((v) => !v)}
                        className="absolute inset-y-0 right-0 flex w-10 items-center justify-center rounded-r-lg text-muted-foreground hover:text-foreground"
                      >
                        {showPassword ? (
                          <EyeOff className="size-4" aria-hidden="true" />
                        ) : (
                          <Eye className="size-4" aria-hidden="true" />
                        )}
                      </button>
                    </div>
                    <FieldError id="auth-password-err" message={passwordError} />
                  </div>

                  {submitError && (
                    <div
                      role="alert"
                      className="flex items-start gap-2 rounded-lg border border-destructive/40 bg-destructive-subtle px-3 py-2.5 text-xs text-destructive"
                    >
                      <AlertCircle className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
                      <span>{submitError}</span>
                    </div>
                  )}

                  <Button type="submit" disabled={submitting} className="h-10 w-full">
                    {submitting && (
                      <Loader2 className="mr-2 size-4 animate-spin" aria-hidden="true" />
                    )}
                    {mode === "login" ? "进入工作台" : "创建账号并登录"}
                  </Button>
                </div>
              </form>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </main>
  );
}
