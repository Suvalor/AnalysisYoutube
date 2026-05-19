import { describe, it, expect } from "vitest";
import { hasRole } from "@/config/features";
import { UserRole, ROLE_PRIORITY } from "@/types/auth";

describe("ROLE_PRIORITY 映射", () => {
  it("应包含所有 UserRole 枚举值", () => {
    const expectedRoles = Object.values(UserRole);
    const mappedRoles = Object.keys(ROLE_PRIORITY);
    expectedRoles.forEach((role) => {
      expect(mappedRoles).toContain(role);
    });
  });

  it("角色优先级应为 guest < user < subscriber < admin", () => {
    expect(ROLE_PRIORITY[UserRole.GUEST]).toBeLessThan(ROLE_PRIORITY[UserRole.USER]);
    expect(ROLE_PRIORITY[UserRole.USER]).toBeLessThan(ROLE_PRIORITY[UserRole.SUBSCRIBER]);
    expect(ROLE_PRIORITY[UserRole.SUBSCRIBER]).toBeLessThan(ROLE_PRIORITY[UserRole.ADMIN]);
  });
});

describe("hasRole 角色层级判断", () => {
  it("游客不能访问 user 级别功能", () => {
    expect(hasRole(UserRole.GUEST, UserRole.USER)).toBe(false);
  });

  it("游客不能访问 subscriber 级别功能", () => {
    expect(hasRole(UserRole.GUEST, UserRole.SUBSCRIBER)).toBe(false);
  });

  it("游客不能访问 admin 级别功能", () => {
    expect(hasRole(UserRole.GUEST, UserRole.ADMIN)).toBe(false);
  });

  it("游客可以访问 guest 级别功能", () => {
    expect(hasRole(UserRole.GUEST, UserRole.GUEST)).toBe(true);
  });

  it("user 可以访问 guest 和 user 级别功能", () => {
    expect(hasRole(UserRole.USER, UserRole.GUEST)).toBe(true);
    expect(hasRole(UserRole.USER, UserRole.USER)).toBe(true);
  });

  it("user 不能访问 subscriber 和 admin 级别功能", () => {
    expect(hasRole(UserRole.USER, UserRole.SUBSCRIBER)).toBe(false);
    expect(hasRole(UserRole.USER, UserRole.ADMIN)).toBe(false);
  });

  it("subscriber 可以访问 guest、user、subscriber 级别功能", () => {
    expect(hasRole(UserRole.SUBSCRIBER, UserRole.GUEST)).toBe(true);
    expect(hasRole(UserRole.SUBSCRIBER, UserRole.USER)).toBe(true);
    expect(hasRole(UserRole.SUBSCRIBER, UserRole.SUBSCRIBER)).toBe(true);
  });

  it("subscriber 不能访问 admin 级别功能", () => {
    expect(hasRole(UserRole.SUBSCRIBER, UserRole.ADMIN)).toBe(false);
  });

  it("admin 可以访问所有级别功能", () => {
    expect(hasRole(UserRole.ADMIN, UserRole.GUEST)).toBe(true);
    expect(hasRole(UserRole.ADMIN, UserRole.USER)).toBe(true);
    expect(hasRole(UserRole.ADMIN, UserRole.SUBSCRIBER)).toBe(true);
    expect(hasRole(UserRole.ADMIN, UserRole.ADMIN)).toBe(true);
  });

  it("currentRole 为 undefined 时应返回 false，防止越权", () => {
    expect(hasRole(undefined, UserRole.GUEST)).toBe(false);
    expect(hasRole(undefined, UserRole.USER)).toBe(false);
    expect(hasRole(undefined, UserRole.ADMIN)).toBe(false);
  });

  it("currentRole 为 null 时应返回 false，防止越权", () => {
    expect(hasRole(null, UserRole.GUEST)).toBe(false);
    expect(hasRole(null, UserRole.USER)).toBe(false);
  });
});

describe("UserRole 枚举完整性", () => {
  it("应包含 guest、user、subscriber、admin 四个值", () => {
    const roles = Object.values(UserRole);
    expect(roles).toContain("guest");
    expect(roles).toContain("user");
    expect(roles).toContain("subscriber");
    expect(roles).toContain("admin");
    expect(roles).toHaveLength(4);
  });
});
