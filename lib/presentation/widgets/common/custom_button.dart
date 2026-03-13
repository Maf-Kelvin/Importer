// lib/presentation/widgets/common/custom_button.dart
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';

class CustomButton extends StatelessWidget {
  final VoidCallback? onPressed;
  final Widget child;
  final ButtonType type;
  final Size? minimumSize;
  final EdgeInsetsGeometry? padding;
  final BorderRadius? borderRadius;

  const CustomButton({
    super.key,
    required this.onPressed,
    required this.child,
    this.type = ButtonType.elevated,
    this.minimumSize,
    this.padding,
    this.borderRadius,
  });

  @override
  Widget build(BuildContext context) {
    final defaultPadding = EdgeInsets.symmetric(horizontal: 24.w, vertical: 12.h);
    final defaultMinimumSize = Size(double.infinity, 48.h);
    final defaultBorderRadius = BorderRadius.circular(8.r);

    switch (type) {
      case ButtonType.elevated:
        return ElevatedButton(
          onPressed: onPressed,
          style: ElevatedButton.styleFrom(
            minimumSize: minimumSize ?? defaultMinimumSize,
            padding: padding ?? defaultPadding,
            shape: RoundedRectangleBorder(
              borderRadius: borderRadius ?? defaultBorderRadius,
            ),
          ),
          child: child,
        );

      case ButtonType.outlined:
        return OutlinedButton(
          onPressed: onPressed,
          style: OutlinedButton.styleFrom(
            minimumSize: minimumSize ?? defaultMinimumSize,
            padding: padding ?? defaultPadding,
            shape: RoundedRectangleBorder(
              borderRadius: borderRadius ?? defaultBorderRadius,
            ),
          ),
          child: child,
        );

      case ButtonType.text:
        return TextButton(
          onPressed: onPressed,
          style: TextButton.styleFrom(
            minimumSize: minimumSize,
            padding: padding ?? EdgeInsets.symmetric(horizontal: 16.w, vertical: 8.h),
            shape: RoundedRectangleBorder(
              borderRadius: borderRadius ?? defaultBorderRadius,
            ),
          ),
          child: child,
        );
    }
  }
}

enum ButtonType { elevated, outlined, text }