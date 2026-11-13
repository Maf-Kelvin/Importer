import '../../core/format.dart';

class ItemModel {
  const ItemModel({
    required this.id,
    required this.containerId,
    required this.name,
    required this.category,
    required this.condition,
    required this.purchasePrice,
    required this.currency,
    required this.weight,
    required this.landedCost,
    required this.sold,
    required this.sellingPrice,
    this.description,
  });

  final int id;
  final int containerId;
  final String name;
  final String? description;
  final String category;
  final String condition;
  final num purchasePrice;
  final String currency;
  final num? weight;
  final num landedCost;
  final bool sold;
  final num? sellingPrice;

  factory ItemModel.fromJson(Map<String, dynamic> j) => ItemModel(
        id: j['id'] as int,
        containerId: (j['container_id'] as int?) ?? 0,
        name: j['name'] as String,
        description: j['description'] as String?,
        category: (j['category'] as String?) ?? '',
        condition: (j['condition'] as String?) ?? '',
        purchasePrice: asNum(j['purchase_price']) ?? 0,
        currency: (j['purchase_currency'] as String?) ?? 'USD',
        weight: asNum(j['weight']),
        landedCost: asNum(j['landed_cost']) ?? 0,
        sold: (j['sold'] as bool?) ?? false,
        sellingPrice: asNum(j['selling_price']),
      );
}

class ExpenseModel {
  const ExpenseModel({required this.id, required this.type, required this.amount, required this.currency, required this.amountUsd, this.description});

  final int id;
  final String type;
  final num amount;
  final String currency;
  final num amountUsd;
  final String? description;

  factory ExpenseModel.fromJson(Map<String, dynamic> j) => ExpenseModel(
        id: j['id'] as int,
        type: (j['expense_type'] as String?) ?? '',
        amount: asNum(j['amount']) ?? 0,
        currency: (j['currency'] as String?) ?? 'USD',
        amountUsd: asNum(j['amount_usd']) ?? 0,
        description: j['description'] as String?,
      );
}

class ContainerDetail {
  const ContainerDetail({
    required this.id,
    required this.name,
    required this.type,
    required this.sealed,
    required this.shipped,
    required this.allocationMethod,
    required this.items,
    required this.expenses,
    required this.totalExpenses,
    required this.totalValue,
    required this.itemsSold,
  });

  final int id;
  final String name;
  final String type;
  final bool sealed;
  final bool shipped;
  final String allocationMethod;
  final List<ItemModel> items;
  final List<ExpenseModel> expenses;
  final num? totalExpenses;
  final num? totalValue;
  final int itemsSold;

  String get status => shipped ? 'Shipped' : (sealed ? 'Sealed' : 'Open');

  factory ContainerDetail.fromJson(Map<String, dynamic> j) => ContainerDetail(
        id: j['id'] as int,
        name: j['name'] as String,
        type: (j['container_type'] as String?) ?? '',
        sealed: (j['is_sealed'] as bool?) ?? false,
        shipped: (j['is_shipped'] as bool?) ?? false,
        allocationMethod: (j['allocation_method'] as String?) ?? '',
        items: ((j['items'] as List?) ?? const []).map((e) => ItemModel.fromJson(e as Map<String, dynamic>)).toList(),
        expenses: ((j['expenses'] as List?) ?? const []).map((e) => ExpenseModel.fromJson(e as Map<String, dynamic>)).toList(),
        totalExpenses: asNum(j['total_expenses']),
        totalValue: asNum(j['total_value']),
        itemsSold: (j['items_sold'] as num?)?.toInt() ?? 0,
      );
}
