import { expect, test } from '@playwright/test';
import { signIn } from './helpers';

const username = process.env.E2E_ADMIN_USERNAME;
const password = process.env.E2E_ADMIN_PASSWORD;

test.skip(!username || !password, 'Set E2E_ADMIN_USERNAME and E2E_ADMIN_PASSWORD to run the end-to-end tests');

test('an admin adds a viewer, the audit log records it, and the viewer sees no admin pages', async ({ page }) => {
  await signIn(page, username!, password!);

  // ---- add a team member ----
  await page.getByRole('link', { name: 'Team' }).click();
  await expect(page.getByRole('heading', { name: 'Team' })).toBeVisible();
  await page.getByRole('button', { name: 'Add member' }).click();
  const stamp = Date.now();
  const newUser = `e2e_viewer_${stamp}`;
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('First name').fill('Vera');
  await dialog.getByLabel('Last name').fill('Viewer');
  await dialog.getByLabel('Email').fill(`${newUser}@example.com`);
  await dialog.getByLabel('Username').fill(newUser);
  await dialog.getByLabel('Initial password').fill('e2e-Strong-Passw0rd!');
  await dialog.getByLabel('Role').selectOption('viewer');
  await dialog.getByRole('button', { name: 'Add member' }).click();
  await expect(page.getByText(newUser)).toBeVisible();

  // ---- the audit log shows who did it ----
  await page.getByRole('link', { name: 'Audit log' }).click();
  await page.getByLabel('Action').selectOption('user.');
  await expect(page.getByText('user.created').first()).toBeVisible();

  // ---- an admin cannot demote their own account ----
  await page.getByRole('link', { name: 'Team' }).click();
  await page.getByRole('row', { name: /\(you\)/ }).getByRole('button', { name: /^Edit / }).click();
  await expect(page.getByRole('dialog').getByLabel('Role')).toBeDisabled();
  await expect(page.getByRole('dialog').getByLabel('Account is active')).toBeDisabled();

  // ---- sign out, then sign in as the viewer ----
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'Sign out' }).first().click();
  await expect(page).toHaveURL(/\/login/);
  await page.getByLabel('Username').fill(newUser);
  await page.getByLabel('Password').fill('e2e-Strong-Passw0rd!');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  await expect(page.getByText('Administration')).toHaveCount(0);

  // ---- and a viewer who types the address gets a clear message, not a broken page ----
  await page.goto('/admin/users');
  await expect(page.getByText("You don't have access to this page")).toBeVisible();
});
