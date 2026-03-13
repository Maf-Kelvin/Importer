// lib/core/utils/responsive.dart
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';

class Responsive {
  // Breakpoints
  static const double mobileBreakpoint = 600;
  static const double tabletBreakpoint = 900;
  static const double desktopBreakpoint = 1200;
  
  // Screen Type Detection
  static bool isMobile(BuildContext context) => 
      MediaQuery.of(context).size.width < mobileBreakpoint;
  
  static bool isTablet(BuildContext context) => 
      MediaQuery.of(context).size.width >= mobileBreakpoint &&
      MediaQuery.of(context).size.width < tabletBreakpoint;
  
  static bool isDesktop(BuildContext context) => 
      MediaQuery.of(context).size.width >= tabletBreakpoint;
  
  // Responsive Values
  static T value<T>({
    required BuildContext context,
    required T mobile,
    T? tablet,
    T? desktop,
  }) {
    if (isDesktop(context) && desktop != null) return desktop;
    if (isTablet(context) && tablet != null) return tablet;
    return mobile;
  }
  
  // Responsive Spacing
  static double spacing(double mobile, [double? tablet, double? desktop]) {
    return Responsive.value(
      context: ScreenUtil().getCurrentContext(),
      mobile: mobile.w,
      tablet: tablet?.w,
      desktop: desktop?.w,
    );
  }
  
  // Responsive Font Size
  static double fontSize(double size) => size.sp;
  
  // Responsive Width/Height
  static double width(double width) => width.w;
  static double height(double height) => height.h;
  
  // Grid Columns
  static int gridColumns(BuildContext context) {
    return Responsive.value(
      context: context,
      mobile: 1,
      tablet: 2,
      desktop: 3,
    );
  }
}