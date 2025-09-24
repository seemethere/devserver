/*
Copyright 2025.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package controller

import (
	"context"
	"fmt"
	"time"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/apimachinery/pkg/util/intstr"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	logf "sigs.k8s.io/controller-runtime/pkg/log"

	devserversv1 "github.com/seemethere/devserver/api/v1"
)

const (
	// DevServerFinalizer is the finalizer added to DevServer resources
	DevServerFinalizer = "devserver.devservers.io/finalizer"
)

// DevServerReconciler reconciles a DevServer object
type DevServerReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

// +kubebuilder:rbac:groups=devservers.devservers.io,resources=devservers,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=devservers.devservers.io,resources=devservers/status,verbs=get;update;patch
// +kubebuilder:rbac:groups=devservers.devservers.io,resources=devservers/finalizers,verbs=update
// +kubebuilder:rbac:groups=devservers.devservers.io,resources=devserverflavors,verbs=get;list;watch
// +kubebuilder:rbac:groups="",resources=pods,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups="",resources=services,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups="",resources=persistentvolumeclaims,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=apps,resources=deployments,verbs=get;list;watch;create;update;patch;delete

// Reconcile is part of the main kubernetes reconciliation loop which aims to
// move the current state of the cluster closer to the desired state.
func (r *DevServerReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := logf.FromContext(ctx)

	// Fetch the DevServer instance
	devServer := &devserversv1.DevServer{}
	err := r.Get(ctx, req.NamespacedName, devServer)
	if err != nil {
		if errors.IsNotFound(err) {
			// Request object not found, could have been deleted after reconcile request
			log.Info("DevServer resource not found. Ignoring since object must be deleted")
			return ctrl.Result{}, nil
		}
		// Error reading the object - requeue the request
		log.Error(err, "Failed to get DevServer")
		return ctrl.Result{}, err
	}

	// Handle deletion
	if devServer.ObjectMeta.DeletionTimestamp.IsZero() {
		// The object is not being deleted, so if it does not have our finalizer,
		// then add the finalizer and update the object
		if !controllerutil.ContainsFinalizer(devServer, DevServerFinalizer) {
			controllerutil.AddFinalizer(devServer, DevServerFinalizer)
			return ctrl.Result{}, r.Update(ctx, devServer)
		}
	} else {
		// The object is being deleted
		if controllerutil.ContainsFinalizer(devServer, DevServerFinalizer) {
			// Our finalizer is present, so lets handle any external dependency
			if err := r.cleanupDevServer(ctx, devServer); err != nil {
				// If fail to delete the external dependency here, return with error
				// so that it can be retried
				return ctrl.Result{}, err
			}

			// Remove our finalizer from the list and update it
			controllerutil.RemoveFinalizer(devServer, DevServerFinalizer)
			if err := r.Update(ctx, devServer); err != nil {
				return ctrl.Result{}, err
			}
		}
		// Stop reconciliation as the item is being deleted
		return ctrl.Result{}, nil
	}

	// Main reconciliation logic
	return r.reconcileDevServer(ctx, devServer)
}

// cleanupDevServer handles cleanup when a DevServer is being deleted
func (r *DevServerReconciler) cleanupDevServer(ctx context.Context, devServer *devserversv1.DevServer) error {
	log := logf.FromContext(ctx)
	log.Info("Cleaning up DevServer resources", "devserver", devServer.Name)

	// Delete associated resources (Deployment, Service, PVCs)
	// Note: In a real implementation, you might want to preserve PVCs for data safety
	// depending on your use case

	// For now, just log the cleanup
	log.Info("DevServer cleanup completed", "devserver", devServer.Name)
	return nil
}

// reconcileDevServer handles the main reconciliation logic
func (r *DevServerReconciler) reconcileDevServer(ctx context.Context, devServer *devserversv1.DevServer) (ctrl.Result, error) {
	log := logf.FromContext(ctx)
	log.Info("Reconciling DevServer", "devserver", devServer.Name, "mode", devServer.Spec.Mode)

	// Fetch the DevServerFlavor
	flavor := &devserversv1.DevServerFlavor{}
	flavorKey := types.NamespacedName{
		Name:      devServer.Spec.Flavor,
		Namespace: devServer.Namespace,
	}
	if err := r.Get(ctx, flavorKey, flavor); err != nil {
		if errors.IsNotFound(err) {
			log.Error(err, "DevServerFlavor not found", "flavor", devServer.Spec.Flavor)
			// Update status to indicate the flavor is missing
			devServer.Status.Phase = "Failed"
			r.Status().Update(ctx, devServer)
			return ctrl.Result{RequeueAfter: time.Minute * 5}, nil
		}
		return ctrl.Result{}, err
	}

	// For now, only handle standalone mode (Phase 3 requirement)
	if devServer.Spec.Mode == "distributed" {
		log.Info("Distributed mode not yet implemented", "devserver", devServer.Name)
		devServer.Status.Phase = "Pending"
		r.Status().Update(ctx, devServer)
		return ctrl.Result{RequeueAfter: time.Minute * 5}, nil
	}

	// Handle standalone mode
	if err := r.reconcileStandaloneServer(ctx, devServer, flavor); err != nil {
		log.Error(err, "Failed to reconcile standalone server")
		devServer.Status.Phase = "Failed"
		r.Status().Update(ctx, devServer)
		return ctrl.Result{}, err
	}

	// Update status
	devServer.Status.Phase = "Running"
	devServer.Status.Ready = true
	if devServer.Status.StartTime == nil {
		now := metav1.Now()
		devServer.Status.StartTime = &now
	}

	if err := r.Status().Update(ctx, devServer); err != nil {
		log.Error(err, "Failed to update DevServer status")
		return ctrl.Result{}, err
	}

	log.Info("DevServer reconciliation completed", "devserver", devServer.Name)
	return ctrl.Result{RequeueAfter: time.Minute * 30}, nil
}

// reconcileStandaloneServer creates/updates resources for a standalone DevServer
func (r *DevServerReconciler) reconcileStandaloneServer(ctx context.Context, devServer *devserversv1.DevServer, flavor *devserversv1.DevServerFlavor) error {
	log := logf.FromContext(ctx)

	// Create or update PVC for home directory
	if err := r.reconcilePVC(ctx, devServer); err != nil {
		return fmt.Errorf("failed to reconcile PVC: %w", err)
	}

	// Create or update Deployment
	if err := r.reconcileDeployment(ctx, devServer, flavor); err != nil {
		return fmt.Errorf("failed to reconcile Deployment: %w", err)
	}

	// Create or update Service (if SSH is enabled)
	if devServer.Spec.EnableSSH {
		if err := r.reconcileService(ctx, devServer); err != nil {
			return fmt.Errorf("failed to reconcile Service: %w", err)
		}
	}

	log.Info("Standalone server reconciliation completed", "devserver", devServer.Name)
	return nil
}

// reconcilePVC creates or updates the PVC for the DevServer home directory
func (r *DevServerReconciler) reconcilePVC(ctx context.Context, devServer *devserversv1.DevServer) error {
	pvcName := fmt.Sprintf("%s-home", devServer.Name)
	pvc := &corev1.PersistentVolumeClaim{}
	pvcKey := types.NamespacedName{Name: pvcName, Namespace: devServer.Namespace}

	// Check if PVC already exists
	err := r.Get(ctx, pvcKey, pvc)
	if err != nil && !errors.IsNotFound(err) {
		return err
	}

	pvcExists := err == nil

	if !pvcExists {
		// Create new PVC
		pvc = &corev1.PersistentVolumeClaim{
			ObjectMeta: metav1.ObjectMeta{
				Name:      pvcName,
				Namespace: devServer.Namespace,
			},
			Spec: corev1.PersistentVolumeClaimSpec{
				AccessModes: []corev1.PersistentVolumeAccessMode{
					corev1.ReadWriteOnce,
				},
				Resources: corev1.VolumeResourceRequirements{
					Requests: corev1.ResourceList{
						corev1.ResourceStorage: devServer.Spec.PersistentHomeSize,
					},
				},
			},
		}

		// Set DevServer as owner
		if err := controllerutil.SetControllerReference(devServer, pvc, r.Scheme); err != nil {
			return err
		}

		if err := r.Create(ctx, pvc); err != nil {
			return err
		}

		logf.FromContext(ctx).Info("PVC created", "pvc", pvcName)
	} else {
		// PVC exists, just ensure ownership (only update mutable metadata)
		updated := false
		if pvc.GetOwnerReferences() == nil || len(pvc.GetOwnerReferences()) == 0 {
			if err := controllerutil.SetControllerReference(devServer, pvc, r.Scheme); err != nil {
				return err
			}
			updated = true
		}

		if updated {
			if err := r.Update(ctx, pvc); err != nil {
				return err
			}
			logf.FromContext(ctx).Info("PVC ownership updated", "pvc", pvcName)
		}
	}

	return nil
}

// reconcileDeployment creates or updates the Deployment for the DevServer
func (r *DevServerReconciler) reconcileDeployment(ctx context.Context, devServer *devserversv1.DevServer, flavor *devserversv1.DevServerFlavor) error {
	deploymentName := devServer.Name
	deployment := &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      deploymentName,
			Namespace: devServer.Namespace,
		},
	}

	op, err := controllerutil.CreateOrUpdate(ctx, r.Client, deployment, func() error {
		// Set DevServer as owner
		if err := controllerutil.SetControllerReference(devServer, deployment, r.Scheme); err != nil {
			return err
		}

		// Configure deployment spec
		replicas := int32(1)
		deployment.Spec = appsv1.DeploymentSpec{
			Replicas: &replicas,
			Selector: &metav1.LabelSelector{
				MatchLabels: map[string]string{
					"app":       "devserver",
					"devserver": devServer.Name,
				},
			},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: map[string]string{
						"app":       "devserver",
						"devserver": devServer.Name,
					},
				},
				Spec: corev1.PodSpec{
					Containers: []corev1.Container{
						{
							Name:  "devserver",
							Image: devServer.Spec.Image,
							// Add default command to keep container running
							Command: []string{"sleep"},
							Args:    []string{"infinity"},
							Resources: corev1.ResourceRequirements{
								Requests: flavor.Spec.Resources.Requests,
								Limits:   flavor.Spec.Resources.Limits,
							},
							VolumeMounts: []corev1.VolumeMount{
								{
									Name:      "home",
									MountPath: "/home/dev",
								},
							},
							Env: []corev1.EnvVar{
								{
									Name:  "DEVSERVER_OWNER",
									Value: devServer.Spec.Owner,
								},
								{
									Name:  "DEVSERVER_MODE",
									Value: devServer.Spec.Mode,
								},
							},
						},
					},
					Volumes: []corev1.Volume{
						{
							Name: "home",
							VolumeSource: corev1.VolumeSource{
								PersistentVolumeClaim: &corev1.PersistentVolumeClaimVolumeSource{
									ClaimName: fmt.Sprintf("%s-home", devServer.Name),
								},
							},
						},
					},
					NodeSelector: flavor.Spec.NodeSelector,
					Tolerations:  flavor.Spec.Tolerations,
				},
			},
		}

		// Add shared volume if specified
		if devServer.Spec.SharedVolumeClaimName != "" {
			deployment.Spec.Template.Spec.Containers[0].VolumeMounts = append(
				deployment.Spec.Template.Spec.Containers[0].VolumeMounts,
				corev1.VolumeMount{
					Name:      "shared",
					MountPath: "/shared",
				},
			)
			deployment.Spec.Template.Spec.Volumes = append(
				deployment.Spec.Template.Spec.Volumes,
				corev1.Volume{
					Name: "shared",
					VolumeSource: corev1.VolumeSource{
						PersistentVolumeClaim: &corev1.PersistentVolumeClaimVolumeSource{
							ClaimName: devServer.Spec.SharedVolumeClaimName,
						},
					},
				},
			)
		}

		return nil
	})

	if err != nil {
		return err
	}

	if op != controllerutil.OperationResultNone {
		logf.FromContext(ctx).Info("Deployment reconciled", "deployment", deploymentName, "operation", op)
	}

	return nil
}

// reconcileService creates or updates the Service for SSH access
func (r *DevServerReconciler) reconcileService(ctx context.Context, devServer *devserversv1.DevServer) error {
	serviceName := fmt.Sprintf("%s-ssh", devServer.Name)
	service := &corev1.Service{
		ObjectMeta: metav1.ObjectMeta{
			Name:      serviceName,
			Namespace: devServer.Namespace,
		},
	}

	op, err := controllerutil.CreateOrUpdate(ctx, r.Client, service, func() error {
		// Set DevServer as owner
		if err := controllerutil.SetControllerReference(devServer, service, r.Scheme); err != nil {
			return err
		}

		// Configure service spec
		service.Spec = corev1.ServiceSpec{
			Selector: map[string]string{
				"app":       "devserver",
				"devserver": devServer.Name,
			},
			Ports: []corev1.ServicePort{
				{
					Name:       "ssh",
					Port:       22,
					TargetPort: intstr.FromInt(22),
					Protocol:   corev1.ProtocolTCP,
				},
			},
			Type: corev1.ServiceTypeClusterIP,
		}

		return nil
	})

	if err != nil {
		return err
	}

	if op != controllerutil.OperationResultNone {
		logf.FromContext(ctx).Info("Service reconciled", "service", serviceName, "operation", op)
		// Update status with SSH endpoint
		devServer.Status.SSHEndpoint = fmt.Sprintf("%s.%s.svc.cluster.local:22", serviceName, devServer.Namespace)
		devServer.Status.ServiceName = serviceName
	}

	return nil
}

// SetupWithManager sets up the controller with the Manager.
func (r *DevServerReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&devserversv1.DevServer{}).
		Owns(&appsv1.Deployment{}).
		Owns(&corev1.Service{}).
		Owns(&corev1.PersistentVolumeClaim{}).
		Named("devserver").
		Complete(r)
}
