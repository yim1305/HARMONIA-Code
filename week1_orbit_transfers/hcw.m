%% HCW
clc; clear; close all;
fig_dir = fullfile(fileparts(mfilename('fullpath')), 'figures'); % save figures here
if ~exist(fig_dir, 'dir'); mkdir(fig_dir); end

R_earth = 6371008.7714; % m
mu = 3.986004418*10^14; % m^3/s^2
alt = 500*10^3; % m
N = 2000; % number of data points
num_orbits = 2;
arrow_start = [100 700 700];
head_size = 0.03;

R = R_earth + alt;
n = sqrt(mu/R^3); % rad/s
period = 2*pi/n; % s
t = linspace(0,num_orbits*period,N);
time = t/period;
one_orbit = 1:N/num_orbits;
label_idx = N/num_orbits/2;

%% Initial conditions
% state is [x; y; xdot; ydot], x is radial and y is along-track
% family 1, varying x0 with no drift condition ydot0 = -2*n*x0
x0_list = 50:50:500; % m
S0_1 = [x0_list; zeros(size(x0_list)); zeros(size(x0_list)); -2*n*x0_list];

% family 2, fixed x0 and varying ydot0 around no drift condition
x0 = 100; % m
ydot_ratio = [0.8 0.9 0.95 1 1.05 1.1 1.2];
S0_2 = [x0*ones(size(ydot_ratio)); zeros(size(ydot_ratio)); zeros(size(ydot_ratio)); -2*n*x0*ydot_ratio];

% family 3, start at target and varying xdot0
xdot0_list = 0.025:0.025:0.25; % m/s
S0_3 = [zeros(size(xdot0_list)); zeros(size(xdot0_list)); xdot0_list; zeros(size(xdot0_list))];

%% Propagate
state_store1 = zeros(4,size(S0_1,2),N);
state_store2 = zeros(4,size(S0_2,2),N);
state_store3 = zeros(4,size(S0_3,2),N);

for i = 1:1:N
    Phi = cw_stm(n,t(i));
    state_store1(:,:,i) = Phi*S0_1;
    state_store2(:,:,i) = Phi*S0_2;
    state_store3(:,:,i) = Phi*S0_3;
end

%% Plot
figure(1);
hold on;
plot(0,0,'r*','MarkerSize',10);
plot(S0_1(2,:),S0_1(1,:),'ko','MarkerFaceColor','k');
for j = 1:1:size(S0_1,2)
    x_traj = squeeze(state_store1(1,j,one_orbit))';
    y_traj = squeeze(state_store1(2,j,one_orbit))';
    surface([y_traj;y_traj],[x_traj;x_traj],zeros(2,N/num_orbits),[time(one_orbit);time(one_orbit)],'FaceColor','none','EdgeColor','interp','LineWidth',2);
    text(y_traj(end),x_traj(end),"  " + string(x0_list(j)) + " m",'FontSize',8);
end
x_arrow = squeeze(state_store1(1,:,:));
y_arrow = squeeze(state_store1(2,:,:));
s = head_size*max(abs(y_arrow(:)));
for j = 1:1:size(S0_1,2)
    arrow_head(y_arrow(j,arrow_start(1)),x_arrow(j,arrow_start(1)),y_arrow(j,arrow_start(1)+1)-y_arrow(j,arrow_start(1)),x_arrow(j,arrow_start(1)+1)-x_arrow(j,arrow_start(1)),s);
end
view(2);
cb = colorbar;
cb.Label.String = 'Time (orbits)';
grid on;
axis equal;
xlabel('Along-track y in target LVLH frame (m)');
ylabel('Radial x in target LVLH frame (m)');
title({'HCW Family 1: Varying x_0 with ydot_0 = -2nx_0 (1 orbit, labels = x_0)', 'Target LVLH frame, x, y, xdot, ydot relative to target'});
legend(["Target", "Start"],'Location','best');
exportgraphics(gcf, fullfile(fig_dir, 'hcw_family1.png'));

figure(2);
hold on;
plot(0,0,'r*','MarkerSize',10);
plot(S0_2(2,1),S0_2(1,1),'ko','MarkerFaceColor','k');
for j = 1:1:size(S0_2,2)
    x_traj = squeeze(state_store2(1,j,:))';
    y_traj = squeeze(state_store2(2,j,:))';
    surface([y_traj;y_traj],[x_traj;x_traj],zeros(2,N),[time;time],'FaceColor','none','EdgeColor','interp','LineWidth',2);
    text(y_traj(end),x_traj(end),"  " + string(ydot_ratio(j)),'FontSize',8);
end
x_arrow = squeeze(state_store2(1,:,:));
y_arrow = squeeze(state_store2(2,:,:));
s = head_size*max(abs(y_arrow(:)));
for j = 1:1:size(S0_2,2)
    arrow_head(y_arrow(j,arrow_start(2)),x_arrow(j,arrow_start(2)),y_arrow(j,arrow_start(2)+1)-y_arrow(j,arrow_start(2)),x_arrow(j,arrow_start(2)+1)-x_arrow(j,arrow_start(2)),s);
end
view(2);
cb = colorbar;
cb.Label.String = 'Time (orbits)';
grid on;
axis equal;
xlabel('Along-track y in target LVLH frame (m)');
ylabel('Radial x in target LVLH frame (m)');
title({'HCW Family 2: x_0 = 100 m, Varying ydot_0 (labels = ydot_0 / (-2nx_0))', 'Target LVLH frame, x, y, xdot, ydot relative to target'});
legend(["Target", "Start"],'Location','best');
exportgraphics(gcf, fullfile(fig_dir, 'hcw_family2.png'));

figure(3);
hold on;
plot(0,0,'r*','MarkerSize',10);
for j = 1:1:size(S0_3,2)
    x_traj = squeeze(state_store3(1,j,one_orbit))';
    y_traj = squeeze(state_store3(2,j,one_orbit))';
    surface([y_traj;y_traj],[x_traj;x_traj],zeros(2,N/num_orbits),[time(one_orbit);time(one_orbit)],'FaceColor','none','EdgeColor','interp','LineWidth',2);
    text(y_traj(label_idx),x_traj(label_idx),"  " + string(xdot0_list(j)) + " m/s",'FontSize',8);
end
x_arrow = squeeze(state_store3(1,:,:));
y_arrow = squeeze(state_store3(2,:,:));
s = head_size*max(abs(y_arrow(:)));
for j = 1:1:size(S0_3,2)
    arrow_head(y_arrow(j,arrow_start(3)),x_arrow(j,arrow_start(3)),y_arrow(j,arrow_start(3)+1)-y_arrow(j,arrow_start(3)),x_arrow(j,arrow_start(3)+1)-x_arrow(j,arrow_start(3)),s);
end
view(2);
cb = colorbar;
cb.Label.String = 'Time (orbits)';
grid on;
axis equal;
xlabel('Along-track y in target LVLH frame (m)');
ylabel('Radial x in target LVLH frame (m)');
title({'HCW Family 3: Start at Target, Varying xdot_0 (1 orbit, labels = xdot_0)', 'Target LVLH frame, x, y, xdot, ydot relative to target'});
legend(["Target and start"],'Location','best');
exportgraphics(gcf, fullfile(fig_dir, 'hcw_family3.png'));

function Phi = cw_stm(n,t)
    c = cos(n*t);
    s = sin(n*t);
    M = [4-3*c, 0; 6*(s-n*t), 1];
    N = [s/n, 2*(1-c)/n; -2*(1-c)/n, (4*s-3*n*t)/n];
    S = [3*n*s, 0; 6*n*(c-1), 0];
    T = [c, 2*s; -2*s, 4*c-3];
    Phi = [M, N; S, T];
end

function arrow_head(y,x,dy,dx,s)
    d = [dy; dx]/norm([dy; dx]);
    p = [-d(2); d(1)];
    tip = [y; x] + 0.5*s*d;
    b1 = [y; x] - 0.5*s*d + 0.3*s*p;
    b2 = [y; x] - 0.5*s*d - 0.3*s*p;
    fill([tip(1) b1(1) b2(1)],[tip(2) b1(2) b2(2)],'k');
end
