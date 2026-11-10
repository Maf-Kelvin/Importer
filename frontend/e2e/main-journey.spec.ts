import { expect, test } from '@playwright/test';

const username = process.env.E2E_ADMIN_USERNAME;
const password = process.env.E2E_ADMIN_PASSWORD;

test.skip(!username || !password, 'Set E2E_ADMIN_USERNAME and E2E_ADMIN_PASSWORD to run the end-to-end tests');

test('signed-out visitors are sent to the login page', async ({ page }) => {
  await page.goto('/containers');
  await expect(page).toHaveURL(/\/login/);
});

test('wrong password is rejected with a clear message', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Username').fill(username ?? 'nobody');
  await page.getByLabel('Password').fill('definitely-wrong-password');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('alert')).toContainText('Incorrect username or password');
});

test('sign in, build a container, allocate its costs, sign out', async ({ page }) => {
  // ---- sign in ----
  await page.goto('/');
  await expect(page).toHaveURL(/\/login/);
  await page.getByLabel('Username').fill(username!);
  await page.getByLabel('Password').fill(password!);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();

  // ---- a reload keeps the session (refresh cookie) ----
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();

  // ---- create a container ----
  await page.getByRole('link', { name: 'Containers' }).click();
  await page.getByRole('button', { name: /New container|Create your first container/ }).first().click();
  const name = `E2E container ${Date.now()}`;
  const newContainer = page.getByRole('dialog');
  await newContainer.getByLabel('Name').fill(name);
  await newContainer.getByRole('button', { name: 'Create container' }).click();
  await expect(page.getByRole('heading', { name })).toBeVisible();

  // ---- add an item ----
  await page.getByRole('button', { name: /Add item|Add the first item/ }).first().click();
  const itemDialog = page.getByRole('dialog');
  await itemDialog.getByLabel('Name').fill('Widget');
  await itemDialog.getByLabel('Purchase price').fill('10.00');
  await itemDialog.getByLabel('Weight (kg)').fill('2');
  await itemDialog.getByRole('button', { name: 'Add item' }).click();
  await expect(page.getByRole('cell', { name: /Widget/ })).toBeVisible();

  // ---- add an expense ----
  await page.getByRole('tab', { name: 'Expenses' }).click();
  await page.getByRole('button', { name: /Add expense|Add an expense/ }).first().click();
  const expenseDialog = page.getByRole('dialog');
  await expenseDialog.getByLabel('Amount').fill('20');
  await expenseDialog.getByRole('button', { name: 'Add expense' }).click();
  await expect(page.getByText('Costs are not fully spread')).toBeVisible();

  // ---- allocate costs: one item takes all 20.00 of the expense ----
  await page.getByRole('button', { name: 'Allocate costs' }).click();
  const allocate = page.getByRole('dialog');
  await allocate.getByRole('button', { name: 'Allocate costs' }).click();
  await expect(allocate.getByText('The shares add up exactly')).toBeVisible();
  await expect(allocate.getByRole('cell', { name: '$30.00' })).toBeVisible(); // landed cost = 10 + 20
  await page.keyboard.press('Escape');
  await expect(page.getByText('Costs are not fully spread')).toBeHidden();

  // ---- sign out ----
  await page.getByRole('button', { name: 'Sign out' }).first().click();
  await expect(page).toHaveURL(/\/login/);
});
