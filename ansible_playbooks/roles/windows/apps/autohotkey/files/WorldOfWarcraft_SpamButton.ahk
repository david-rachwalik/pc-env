#IfWinActive World of Warcraft
{
    ; The following script is run when the user presses the '1' key
    ; and will loop until the 1 key is no longer pressed, sending
    ; 1 over and over every delay miliseconds. To use a different
    ; key, replace all three 1s with the key you want repeated.

    delay := 50

	1::
	   Loop
	   {
			if !GetKeyState("1", "P")
			break
			Send 1
			Sleep delay
		}
	return
	2::
		Loop
		{
			if !GetKeyState("2", "P")
			break
			Send 2
			Sleep delay
		}
	return
	3::
		Loop
		{
			if !GetKeyState("3", "P")
			break
			Send 3
			Sleep delay
		}
	return
	4::
	   Loop
	   {
			if !GetKeyState("4", "P")
			break
			Send 4
			Sleep delay
		}
	return
	5::
		Loop
		{
			if !GetKeyState("5", "P")
			break
			Send 5
			Sleep delay
		}
	return
	6::
		Loop
		{
			if !GetKeyState("6", "P")
			break
			Send 6
			Sleep delay
		}
	return
	7::
		Loop
		{
			if !GetKeyState("7", "P")
			break
			Send 7
			Sleep delay
		}
	return
	8::
		Loop
		{
			if !GetKeyState("8", "P")
			break
			Send 8
			Sleep delay
		}
	return
	9::
		Loop
		{
			if !GetKeyState("9", "P")
			break
			Send 9
			Sleep delay
		}
	return
	0::
		Loop
		{
			if !GetKeyState("0", "P")
			break
			Send 0
			Sleep delay
		}
	return
	-::
		Loop
		{
			if !GetKeyState("-", "P")
			break
			Send -
			Sleep delay
		}
	return
	+1::
		Loop
		{
			if !GetKeyState("!", "P")
			break
			Send +1
			Sleep delay
		}
	return
	+2::
		Loop
		{
			if !GetKeyState("@", "P")
			break
			Send +2
			Sleep delay
		}
	return
	+3::
		Loop
		{
			if !GetKeyState("#", "P")
			break
			Send +3
			Sleep delay
		}
	return
	+4::
		Loop
		{
			if !GetKeyState("$", "P")
			break
			Send +4
			Sleep delay
		}
	return
	+5::
		Loop
		{
			if !GetKeyState("%", "P")
			break
			Send +5
			Sleep delay
		}
	return
	+6::
		Loop
		{
			if !GetKeyState("^", "P")
			break
			Send +6
			Sleep delay
		}
	return
	+7::
		Loop
		{
			if !GetKeyState("&", "P")
			break
			Send +7
			Sleep delay
		}
	return
	+8::
		Loop
		{
			if !GetKeyState("*", "P")
			break
			Send +8
			Sleep delay
		}
	return
	+9::
		Loop
		{
			if !GetKeyState("(", "P")
			break
			Send +9
			Sleep delay
		}
	return
	+0::
		Loop
		{
			if !GetKeyState(")", "P")
			break
			Send +0
			Sleep delay
		}
	return
	+-::
		Loop
		{
			if !GetKeyState("_", "P")
			break
			Send +-
			Sleep delay
		}
	return
}
