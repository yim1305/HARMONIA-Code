%% Hohmann
clc; clear; close all;
R_earth = 6371008.7714; % m
mu = 3.986004418*10^14; % m^3/s^2
alt1 = 400*10^3; % m
alt2 = 1200*10^3; % m
N = 5000; % number of data points
R_ratio_max = 11.94;
R1 = R_earth + alt1;
R2 = R_earth + alt2;
v1 = sqrt(mu/R1); % m/s
% for our range
R_range = linspace(R1,R2,N);
R_ratio_store = R_range/R1;
[delta_v1_store, delta_v2_store] = delta_v_calc(mu,R1,R_range);
delta_v1_store = delta_v1_store/v1;
delta_v2_store = delta_v2_store/v1;
delta_v_store = delta_v1_store + delta_v2_store;
% for full range
R_ratio_store2 = logspace(0,log10(R_ratio_max),N);
R_range2 = R_ratio_store2*R1;
[delta_v1_store2, delta_v2_store2] = delta_v_calc(mu,R1,R_range2);
delta_v1_store2 = delta_v1_store2/v1;
delta_v2_store2 = delta_v2_store2/v1;
delta_v_store2 = delta_v1_store2 + delta_v2_store2;
%% Plot
% I'm plotting delta v / v1 for both ranges
% because raw delta v changes with different initial radius and the magnitude of delta v would differ
figure(1);
plot(R_ratio_store,delta_v1_store, '--r');
hold on;
plot(R_ratio_store,delta_v2_store, '--g');
plot(R_ratio_store,delta_v_store, '-b', 'LineWidth', 1.5);
plot(R_ratio_store(end),delta_v_store(end), 'bo', 'MarkerFaceColor', 'b');
text(R_ratio_store(end),delta_v_store(end), sprintf('400 to 1200 km: %.0f m/s  ', delta_v_store(end)*v1), 'HorizontalAlignment', 'right', 'VerticalAlignment', 'bottom');
grid on;
xlabel('Radius Ratio R = r_2/r_1');
ylabel('\Delta v / v_1,  v_1 = \surd(\mu/r_1)');
title('Partial Range (400 km to 1200 km)');
legend('\Delta v_1','\Delta v_2','Total','Location','northwest');
exportgraphics(gcf,'hohmann_partial.png');
figure(2);
semilogx(R_ratio_store2,delta_v1_store2, '--r');
hold on;
semilogx(R_ratio_store2,delta_v2_store2, '--g');
semilogx(R_ratio_store2,delta_v_store2, '-b', 'LineWidth', 1.5);
grid on;
xlabel('Radius Ratio R = r_2/r_1');
ylabel('\Delta v / v_1,  v_1 = \surd(\mu/r_1)');
title('Full Range (R up to 11.94)');
legend('\Delta v_1','\Delta v_2','Total','Location','northwest');
exportgraphics(gcf,'hohmann_full.png');
% for every start and target pair in 400 km to 1200 km
N_grid = 300;
alt_grid = linspace(400*10^3,1200*10^3,N_grid); % m
[alt_start_grid, alt_target_grid] = meshgrid(alt_grid, alt_grid);
[delta_v1_grid, delta_v2_grid] = delta_v_calc(mu, R_earth + alt_start_grid, R_earth + alt_target_grid);
delta_v_grid = abs(delta_v1_grid) + abs(delta_v2_grid); % m/s
figure(3);
contourf(alt_start_grid/10^3, alt_target_grid/10^3, delta_v_grid, 30, 'LineColor', 'none');
hold on;
[C, h] = contour(alt_start_grid/10^3, alt_target_grid/10^3, delta_v_grid, 50:50:400, 'k');
clabel(C, h);
c = colorbar;
c.Label.String = 'Total \Delta v (m/s)';
axis equal tight;
xlabel('Start altitude (km)');
ylabel('Target altitude (km)');
title('Total \Delta v for 400 km to 1200 km');
exportgraphics(gcf,'hohmann_contour.png');
function [delta_vp, delta_va] = delta_v_calc(mu,R1,R2)
    a = (R1+R2)/2;
    e = (R2-R1)./(R2+R1);
    vp = sqrt((mu*(1+e))./(a.*(1-e)));
    va = sqrt((mu*(1-e))./(a.*(1+e)));
    delta_vp = vp - sqrt(mu./(a.*(1-e))); % m/s
    delta_va = sqrt(mu./(a.*(1+e))) - va; % m/s
end
