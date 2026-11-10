import { expect, type Page } from '@playwright/test';

export async function signIn(page: Page, username: string, password: string): Promise<void> {
  await page.goto('/');
  await expect(page).toHaveURL(/\/login/);
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
}

/** Creates a container with one item ("Widget", 10.00, 2 kg) and leaves the browser on its page. */
export async function createContainerWithItem(page: Page, itemName = 'Widget'): Promise<string> {
  await page.getByRole('link', { name: 'Containers' }).click();
  await page.getByRole('button', { name: /New container|Create your first container/ }).first().click();
  const name = `E2E container ${Date.now()}`;
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Name').fill(name);
  await dialog.getByRole('button', { name: 'Create container' }).click();
  await expect(page.getByRole('heading', { name })).toBeVisible();

  await page.getByRole('button', { name: /Add item|Add the first item/ }).first().click();
  const itemDialog = page.getByRole('dialog');
  await itemDialog.getByLabel('Name').fill(itemName);
  await itemDialog.getByLabel('Purchase price').fill('10.00');
  await itemDialog.getByLabel('Weight (kg)').fill('2');
  await itemDialog.getByRole('button', { name: 'Add item' }).click();
  await expect(page.getByRole('cell', { name: new RegExp(itemName) })).toBeVisible();
  return name;
}
