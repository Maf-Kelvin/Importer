// lib/domain/entities/item.dart
import 'package:equatable/equatable.dart';
import 'pricing.dart';

class Item extends Equatable {
  final int id;
  final int containerId;
  final String name;
  final String? description;
  final String category;
  final String condition;
  final double purchasePrice;
  final String purchaseCurrency;
  final String? purchaseDate;
  final double fxRateToUsd;
  final double purchasePriceUsd;
  final double weight;
  final double? volume;
  final double? allocatedCost;
  final double? landedCost;
  final double? recommendedPrice;
  final double? sellingPrice;
  final bool sold;
  final String? soldDate;
  final DateTime createdAt;
  final DateTime updatedAt;
  final List<PriceRecord>? priceRecords;
  final double? profitMargin;
  final double? profitAmount;

  const Item({
    required this.id,
    required this.containerId,
    required this.name,
    this.description,
    required this.category,
    required this.condition,
    required this.purchasePrice,
    required this.purchaseCurrency,
    this.purchaseDate,
    required this.fxRateToUsd,
    required this.purchasePriceUsd,
    required this.weight,
    this.volume,
    this.allocatedCost = 0.0,
    this.landedCost = 0.0,
    this.recommendedPrice,
    this.sellingPrice,
    required this.sold,
    this.soldDate,
    required this.createdAt,
    required this.updatedAt,
    this.priceRecords,
    this.profitMargin,
    this.profitAmount,
  });

  double get actualProfit {
    if (sellingPrice != null && landedCost != null) {
      return sellingPrice! - landedCost!;
    }
    return 0.0;
  }

  double get actualProfitMargin {
    if (sellingPrice != null && landedCost != null && landedCost! > 0) {
      return (sellingPrice! - landedCost!) / landedCost!;
    }
    return 0.0;
  }

  double get potentialProfit {
    if (recommendedPrice != null && landedCost != null) {
      return recommendedPrice! - landedCost!;
    }
    return 0.0;
  }

  String get statusText {
    if (sold) return 'Sold';
    if (recommendedPrice != null) return 'Priced';
    if (landedCost != null && landedCost! > 0) return 'Costed';
    return 'Added';
  }

  bool get hasRecommendedPrice => recommendedPrice != null && recommendedPrice! > 0;
  bool get hasCostAllocation => allocatedCost != null && allocatedCost! > 0;

  @override
  List<Object?> get props => [
        id,
        containerId,
        name,
        description,
        category,
        condition,
        purchasePrice,
        purchaseCurrency,
        purchaseDate,
        fxRateToUsd,
        purchasePriceUsd,
        weight,
        volume,
        allocatedCost,
        landedCost,
        recommendedPrice,
        sellingPrice,
        sold,
        soldDate,
        createdAt,
        updatedAt,
        priceRecords,
        profitMargin,
        profitAmount,
      ];
}