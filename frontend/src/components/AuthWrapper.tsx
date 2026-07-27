"use client";

import React, { useState } from "react";
import { loginSchema, registerSchema, type LoginInput, type RegisterInput } from "@/lib/validation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export function AuthWrapper() {
  const [isLogin, setIsLogin] = useState(true);
  
  const loginForm = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
  });
  
  const registerForm = useForm<RegisterInput>({
    resolver: zodResolver(registerSchema),
  });

  const handleLoginSubmit = async (data: LoginInput) => {
    // ... existing login logic
    console.log("Login:", data);
  };

  const handleRegisterSubmit = async (data: RegisterInput) => {
    // ... existing register logic
    console.log("Register:", data);
  };

  return (
    <div className="w-full max-w-md mx-auto">
      <Tabs value={isLogin ? "login" : "register"} onValueChange={(v) => setIsLogin(v === "login")}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="login">Login</TabsTrigger>
          <TabsTrigger value="register">Register</TabsTrigger>
        </TabsList>
        
        <TabsContent value="login">
          <form onSubmit={loginForm.handleSubmit(handleLoginSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                {...loginForm.register("email")}
              />
              {loginForm.formState.errors.email && (
                <p className="text-sm text-red-500">{loginForm.formState.errors.email.message}</p>
              )}
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                {...loginForm.register("password")}
              />
              {loginForm.formState.errors.password && (
                <p className="text-sm text-red-500">{loginForm.formState.errors.password.message}</p>
              )}
            </div>
            
            <Button type="submit" className="w-full">
              Sign In
            </Button>
          </form>
        </TabsContent>
        
        <TabsContent value="register">
          <form onSubmit={registerForm.handleSubmit(handleRegisterSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="reg_email">Email</Label>
              <Input
                id="reg_email"
                type="email"
                placeholder="you@example.com"
                {...registerForm.register("email")}
              />
              {registerForm.formState.errors.email && (
                <p className="text-sm text-red-500">{registerForm.formState.errors.email.message}</p>
              )}
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="full_name">Full Name (optional)</Label>
              <Input
                id="full_name"
                {...registerForm.register("full_name")}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="reg_password">Password</Label>
              <Input
                id="reg_password"
                type="password"
                {...registerForm.register("password")}
              />
              {registerForm.formState.errors.password && (
                <p className="text-sm text-red-500">{registerForm.formState.errors.password.message}</p>
              )}
            </div>
            
            <Button type="submit" className="w-full">
              Create Account
            </Button>
          </form>
        </TabsContent>
      </Tabs>
    </div>
  );
}