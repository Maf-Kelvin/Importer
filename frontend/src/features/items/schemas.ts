import { z } from 'zod';
import type { Item, ItemCreate } from '@/api/types';
import { CURRENCIES, ITEM_CATEGORIES, ITEM_CONDITIONS } from '@/api/types';
import { MONEY_DECIMALS, WEIGHT_DECIMALS, decimalForInput, requireDecimal } from '@/lib/money';
import { optionalPositiveDecimal, positiveDecimal } from '@/lib/validation';

const positive = positiveDecimal;
const optionalPositive = optionalPositiveDecimal;

/** Every field is text while editing; money is converted to a decimal STRING (never a float) on submit. */
export const itemSchema = z.object({
  name: z.string().trim().min(1, 'Enter a name').max(255, 'At most 255 characters'),
  description: z.string().trim(),
  category: z.enum(ITEM_CATEGORIES),
  condition: z.enum(ITEM_CONDITIONS),
  purchase_price: positive(MONEY_DECIMALS, 'Price'),
  purchase_currency: z.enum(CURRENCIES),
  purchase_date: z.string(),
  weight: positive(WEIGHT_DECIMALS, 'Weight'),
  volume: optionalPositive(WEIGHT_DECIMALS, 'Volume'),
});
export type ItemFormValues = z.infer<typeof itemSchema>;

export const itemDefaults: ItemFormValues = {
  name: '',
  description: '',
  category: 'other',
  condition: 'new',
  purchase_price: '',
  purchase_currency: 'USD',
  purchase_date: '',
  weight: '',
  volume: '',
};

export function valuesFromItem(i: Item): ItemFormValues {
  return {
    name: i.name,
    description: i.description ?? '',
    category: i.category,
    condition: i.condition,
    purchase_price: decimalForInput(i.purchase_price),
    purchase_currency: (CURRENCIES as readonly string[]).includes(i.purchase_currency) ? (i.purchase_currency as ItemFormValues['purchase_currency']) : 'USD',
    purchase_date: i.purchase_date ?? '',
    weight: decimalForInput(i.weight),
    volume: decimalForInput(i.volume),
  };
}

export function toItemBody(v: ItemFormValues): Omit<ItemCreate, 'container_id'> {
  return {
    name: v.name,
    description: v.description || null,
    category: v.category,
    condition: v.condition,
    purchase_price: requireDecimal(v.purchase_price, MONEY_DECIMALS),
    purchase_currency: v.purchase_currency,
    purchase_date: v.purchase_date || null,
    weight: requireDecimal(v.weight, WEIGHT_DECIMALS),
    volume: v.volume ? requireDecimal(v.volume, WEIGHT_DECIMALS) : null,
  };
}

export const soldSchema = z.object({
  selling_price: positive(MONEY_DECIMALS, 'Selling price'),
  sold_date: z.string().min(1, 'Choose the sale date'),
  customer_id: z.string(), // '' = no customer
});
export type SoldFormValues = z.infer<typeof soldSchema>;
