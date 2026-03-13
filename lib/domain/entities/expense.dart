// lib/domain/entities/expense.dart
import 'package:equatable/equatable.dart';

class Expense extends Equatable {
  final int id;
  final int containerId;
  final String expenseType;
  final double amount;
  final String currency;
  final String? description;
  final double fxRateToUsd;
  final double amountUsd;
  final DateTime createdAt;
  final DateTime updatedAt;

  const Expense({
    required this.id,
    required this.containerId,
    required this.expenseType,
    required this.amount,
    required this.currency,
    this.description,
    required this.fxRateToUsd,
    required this.amountUsd,
    required this.createdAt,
    required this.updatedAt,
  });

  String get displayName {
    switch (expenseType) {
      case 'loading_fee':
        return 'Loading Fee';
      case 'shipping_fee':
        return 'Shipping Fee';
      case 'clearing_fee':
        return 'Clearing Fee';
      case 'offloading_fee':
        return 'Offloading Fee';
      case 'warehouse_fee':
        return 'Warehouse Fee';
      case 'security_fee':
        return 'Security Fee';
      case 'extra_fee':
        return 'Extra Fee';
      default:
        return expenseType.replaceAll('_', ' ').toUpperCase();
    }
  }

  @override
  List<Object?> get props => [
        id,
        containerId,
        expenseType,
        amount,
        currency,
        description,
        fxRateToUsd,
        amountUsd,
        createdAt,
        updatedAt,
      ];
}
