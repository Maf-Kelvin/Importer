import { expect, test } from '@playwright/test';
import { createContainerWithItem, signIn } from './helpers';

const username = process.env.E2E_ADMIN_USERNAME;
const password = process.env.E2E_ADMIN_PASSWORD;

test.skip(!username || !password, 'Set E2E_ADMIN_USERNAME and E2E_ADMIN_PASSWORD to run the end-to-end tests');

test('add a customer, price an item, then sell it to that customer', async ({ page }) => {
  await signIn(page, username!, password!);

  // ---- a customer ----
  await page.getByRole('link', { name: 'Customers' }).click();
  await page.getByRole('button', { name: /New customer|Add your first customer/ }).first().click();
  const customerName = `E2E customer ${Date.now()}`;
  const customerDialog = page.getByRole('dialog');
  await customerDialog.getByLabel('Name').fill(customerName);
  await customerDialog.getByRole('button', { name: 'Add customer' }).click();
  await expect(page.getByRole('cell', { name: customerName })).toBeVisible();

  // ---- an item to price and sell ----
  await createContainerWithItem(page);

  // ---- an explainable price recommendation (market scraping switched off: no background job needed) ----
  await page.getByRole('button', { name: 'Price Widget' }).click();
  const pricing = page.getByRole('dialog');
  await pricing.getByLabel('Market prices').uncheck();
  await pricing.getByRole('button', { name: 'Get recommendation' }).click();
  await expect(pricing.getByText('Recommended price')).toBeVisible();
  await expect(pricing.getByRole('progressbar', { name: 'Confidence' })).toBeVisible();
  await expect(pricing.getByRole('heading', { name: 'Why this price' })).toBeVisible();
  await page.keyboard.press('Escape');

  // ---- sell it to the customer ----
  await page.getByRole('button', { name: 'Sell Widget' }).click();
  const sell = page.getByRole('dialog');
  await sell.getByLabel('Selling price (USD)').fill('25');
  await sell.getByLabel('Customer').selectOption({ label: customerName });
  await sell.getByRole('button', { name: 'Record sale' }).click();
  await expect(page.getByText(/Sold \$25\.00/)).toBeVisible();
});
