//+
nx1=41;
nx2=41;
ny=41;
nb=41;
nc=41;
d=0.005;
L=50*d;

Point(1) = {-L, -L, 0, 1.0};
Point(2) = {L, -L, 0, 1.0};
Point(3) = {4*L, -L, 0, 1.0};
Point(4) = {-L, L, 0, 1.0};
Point(5) = {L, L, 0, 1.0};
Point(6) = {4*L, L, 0, 1.0};
//+
Point(7) = {-d, -d, 0, 1.0};
Point(8) = {d, -d, 0, 1.0};
Point(9) = {-d, d, 0, 1.0};
Point(10) = {d, d, 0, 1.0};
Point(11) = {0, 0, 0, 1.0};

Line(1)={1,2};
Line(2)={2,3};
Line(3)={4,5};
Line(4)={5,6};
Line(5)={1,4};
Line(6)={2,5};
Line(7)={3,6};

Circle(8)={7, 11, 8};
Circle(9)={8, 11, 10};
Circle(10)={10, 11, 9};
Circle(11)={9, 11, 7};

Line(12) ={1,7};
Line(13) ={2,8};
Line(14) ={5,10};
Line(15) ={4,9};
//+
Transfinite Curve {3, 1} = nx1 Using Progression 1;
Transfinite Curve {11, 9, 10, 8} = nc Using Progression 1;
//+
Transfinite Curve {15, 12, 13, 14} = nb Using Progression 0.9;
//+
Transfinite Curve {4, 2} = nx2 Using Progression 1;
//+
Transfinite Curve {5, 6, 7} = ny Using Progression 1;
//+
Curve Loop(1) = {5, 15, 11, -12};
//+
Plane Surface(1) = {1};
//+
Curve Loop(2) = {12, 8, -13, -1};
//+
Plane Surface(2) = {2};
//+
Curve Loop(3) = {13, 9, -14, -6};
//+
Plane Surface(3) = {3};
//+
Curve Loop(4) = {14, 10, -15, 3};
//+
Plane Surface(4) = {4};
//+
Curve Loop(5) = {6, 4, -7, -2};
//+
Plane Surface(5) = {5};
//+
Transfinite Surface {1};
//+
Transfinite Surface {4};
//+
Transfinite Surface {3};
//+
Transfinite Surface {2};
//+
Transfinite Surface {5};
//+
Recombine Surface {1, 4, 3, 2, 5};
//+
Physical Curve("inlet", 16) = {5};
//+
Physical Curve("outlet", 17) = {7};
//+
Physical Curve("top", 18) = {3, 4};
//+
Physical Curve("bottom", 19) = {1, 2};
//+
Physical Curve("wall", 20) = {11, 10, 9, 8};
