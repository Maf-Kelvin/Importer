// lib/domain/entities/container.dart
import 'package:equatable/equatable.dart';
import 'item.dart';
import 'expense.dart';

class Container extends Equatable {
  final int id;
  final String name;
  final String containerType;
  final String? mscContainerNumber;
  final String allocationMethod;
  final int ownerId;
  final bool isSealed;
  final bool isShipped;
  final bool allocationOverride;
  final String? notes;
  final DateTime createdAt;
  final DateTime updatedAt;
  final List<Item>? items;
  final List<Expense>? expenses;
  final double? totalExpenses;
  final double? totalWeight;
  final double? totalValue;

  const Container({
    required this.id,
    required this.name,
    required this.containerType,
    this.mscContainerNumber,
    required this.allocationMethod,
    required this.ownerId,
    required this.isSealed,
    required this.isShipped,
    required this.allocationOverride,
    this.notes,
    required this.createdAt,
    required this.updatedAt,
    this.items,
    this.expenses,
    this.totalExpenses,
    this.totalWeight,
    this.totalValue,
  });

  int get itemCount => items?.length ?? 0;
  int get soldItemCount => items?.where((item) => item.sold).length ?? 0;
  double get completionPercentage => 
      itemCount > 0 ? (soldItemCount / itemCount) : 0.0;

  bool get canAddItems => !isSealed;
  bool get hasTracking => mscContainerNumber != null && mscContainerNumber!.isNotEmpty;

  String get statusText {
    if (!isShipped) return 'Preparing';
    if (isShipped && soldItemCount == 0) return 'Shipped';
    if (soldItemCount == itemCount) return 'Completed';
    return 'In Progress';
  }

  @override
  List<Object?> get props => [
        id,
        name,
        containerType,
        mscContainerNumber,
        allocationMethod,
        ownerId,
        isSealed,
        isShipped,
        allocationOverride,
        notes,
        createdAt,
        updatedAt,
        items,
        expenses,
        totalExpenses,
        totalWeight,
        totalValue,
      ];
}