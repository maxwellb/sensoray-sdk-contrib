/////////////////////////////////////////////////////////////////////////////
// Module    : s26app.h
// Function  : 2600 declarations shared by app/module code
// Target OS : MSYS2 UCRT64 (Windows), x86_64-w64-mingw32
// Author    : Jim Lamberson (adapted for MSYS2-UCRT64)
// Copyright : (C) 2008 Sensoray
// Contributor: Maxwell Bloch (github.com/maxwellb), 2026 — MSYS2 UCRT64 (x86_64-w64-mingw32) port.
/////////////////////////////////////////////////////////////////////////////

#ifndef _INC_S26APP_H_
#define _INC_S26APP_H_

// Expose function through the API.
#define EXPORT(RTNTYPE)	RTNTYPE

// Macro used to declare an api function.
#ifndef API
#define API(RTNTYPE,FUNCNAME,ARGS)	RTNTYPE FUNCNAME ARGS
#endif

// Fundamental types.
typedef unsigned char		u8;							// 8-bit unsigned.
typedef unsigned short		u16;						// 16-bit unsigned.
typedef unsigned int		u32;						// 32-bit unsigned.
typedef signed short		s16;						// 16-bit signed.
typedef signed int			s32;						// 32-bit signed.
typedef double				DOUBLE;						// Floating point, double precision.
typedef int					BOOL;						// Boolean.

#endif	// ifdef _INC_S26APP_H_
